# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools

from recipe_engine import recipe_api
from recipe_engine.types import FrozenDict, freeze

from . import bot_db as bot_db_module
from . import bot_spec as bot_spec_module
from . import try_spec as try_spec_module

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.attr_utils import (attrib, attrs, cached_property,
                                             mapping_attrib, sequence_attrib)


class BotConfigException(Exception):
  """Exception indicating an attempt to create an invalid BotConfig."""
  pass


@attrs()
class BotConfig(object):
  """"Static" configuration for a bot.

  BotConfig provides access to information defined entirely in recipes; for a
  given recipe version BotConfig information will be the same for all builds of
  a given builder.

  BotConfig wraps multiple bot specs and provides the means for getting values
  in a manner that ensures they are compatible between all of the wrapped specs.
  BotConfig overrides attribute access so that attempting to access any
  attribute that is defined on the specs returns the value on the specs, raising
  an exception if the value is inconsistent between the specs.
  """

  bot_db = attrib(bot_db_module.BotDatabase)
  bot_mirrors = sequence_attrib(try_spec_module.TryMirror)

  @classmethod
  def create(cls, bot_db, builder_ids_or_bot_mirrors):
    assert len(builder_ids_or_bot_mirrors) >= 1
    bot_db = bot_db_module.BotDatabase.normalize(bot_db)
    bot_mirrors = tuple(
        try_spec_module.TryMirror.normalize(b)
        for b in builder_ids_or_bot_mirrors)
    return cls(bot_db, bot_mirrors)

  def __attrs_post_init__(self):
    for mirror in self.bot_mirrors:
      if not mirror.builder_id.master in self.bot_db.builders_by_master:
        raise BotConfigException(
            'No configuration present for master {!r}'.format(
                mirror.builder_id.master))
      if not mirror.builder_id in self.bot_db:
        raise BotConfigException(
            'No configuration present for builder {}'.format(mirror.builder_id))

  @cached_property
  def builder_ids(self):
    return [m.builder_id for m in self.bot_mirrors]

  @cached_property
  def root_keys(self):
    keys = list(self.builder_ids)
    keys.extend(mirror.tester_id
                for mirror in self.bot_mirrors
                if mirror.tester_id is not None)
    return keys

  @cached_property
  def all_keys(self):
    return self.bot_db.bot_graph.get_transitive_closure(self.root_keys)

  def __getattr__(self, attr):
    per_builder_values = {}
    for builder_id in self.builder_ids:
      bot_spec = self.bot_db[builder_id]
      value = getattr(bot_spec, attr)
      per_builder_values[builder_id] = value
    values = list(set(per_builder_values.values()))
    assert len(values) == 1, 'Inconsistent value for {!r}:\n  {}'.format(
        attr, '\n  '.join('{!r}: {!r}'.format(k, v)
                          for k, v in per_builder_values.iteritems()))
    return values[0]

  def _get_source_side_spec(self, chromium_tests_api, mastername):
    if len(self.builder_ids) == 1:
      builder_id = self.builder_ids[0]
      bot_spec = self.bot_db[builder_id]

      # Some internal builders specify the source side spec using the
      # downstream_spec field of BotSpec instead of reading it from a file
      # If specified, the downstream_spec field holds a dictionary containing
      # the same content as the deserialized JSON of the source side spec would
      # contain
      if bot_spec.downstream_spec is not None:  # pragma: no cover
        return (
            bot_spec.downstream_spec,
            (builder_id, 'downstream_spec', bot_spec.downstream_spec),
        )

    source_side_spec_file = self.source_side_spec_file or '%s.json' % mastername

    return chromium_tests_api.read_source_side_spec(source_side_spec_file), None

  def _get_source_side_specs(self, chromium_tests_api):
    masters = set(key.master for key in self.all_keys)
    specs = {}
    migration = set()
    for master_name in sorted(masters):
      spec, migration_details = self._get_source_side_spec(
          chromium_tests_api, master_name)
      specs[master_name] = spec
      if migration_details is not None:
        migration.add(migration_details)
    if migration:
      step_api = chromium_tests_api.m.step
      json_api = chromium_tests_api.m.json
      with step_api.nest('source side spec migration') as presentation:
        presentation.step_text = (
            '\nThis is an informational step for infra maintainers')
        for builder_id, field, content in sorted(migration):
          step_name = '{}%{}'.format(builder_id.master, builder_id.builder)
          result = step_api(step_name, [])
          result.presentation.logs[field] = json_api.dumps(content, indent=4)

    return specs

  def create_build_config(self, chromium_tests_api, bot_update_step):
    # The scripts_compile_targets is indirected through a function so that we
    # don't execute unnecessary steps if there are no scripts that need to be
    # run
    # Memoize the call to get_compile_targets_for_scripts so that we only
    # execute the step once
    memo = []

    def scripts_compile_targets_fn():
      if not memo:
        memo.append(chromium_tests_api.get_compile_targets_for_scripts(self))
      return memo[0]

    source_side_specs = self._get_source_side_specs(chromium_tests_api)
    tests = {}

    for master_name, source_side_spec in source_side_specs.iteritems():
      builders_for_master = self.bot_db.builders_by_master[master_name]
      for builder_name, builder_spec in builders_for_master.iteritems():
        builder_id = chromium.BuilderId.create_for_master(
            master_name, builder_name)
        builder_tests = chromium_tests_api.generate_tests_from_source_side_spec(
            source_side_spec,
            builder_spec,
            builder_name,
            master_name,
            builder_spec.swarming_dimensions,
            scripts_compile_targets_fn,
            bot_update_step,
        )
        tests[builder_id] = builder_tests

    return BuildConfig(chromium_tests_api, self, source_side_specs, tests)


@attrs()
class BuildConfig(object):
  """"Dynamic" configuration for a bot.

  BuildConfig provides access to information obtained from src-side files; for a
  given recipe version BuildConfig information can change on a per-src-revision
  basis. There could potentially be multiple BuildConfigs for the same build
  that contain different information (e.g. a trybot running against a change
  that modifies the src-side spec information).

  This creates a directed acyclic builder graph, with the builders
  described by the provided bot IDs as the root nodes and the builders
  they trigger as their children. Nodes keep track of whether they're
  referenced by a bot ID (and would thus be mirrored by trybots).
  """

  # TODO(https://crbug.com/1071225) Remove this once we no longer need to track
  # removal of recipe-side configuration values
  # The type is looser than would be nice, but trying to make it a tighter match
  # would cause an import cycle
  _chromium_tests_api = attrib(recipe_api.RecipeApi)
  bot_config = attrib(BotConfig)
  _source_side_specs = mapping_attrib(str, FrozenDict)
  _tests = mapping_attrib(chromium.BuilderId, tuple)

  def _get_tests_for(self, keys):
    tests = []
    for k in keys:
      tests.extend(self._tests[k])
    return tests

  def all_tests(self):
    """Returns all tests."""
    return self._get_tests_for(self.bot_config.all_keys)

  def tests_in_scope(self):
    """Returns all tests for the provided bot IDs."""
    return self._get_tests_for(self.bot_config.root_keys)

  def tests_on(self, builder_id):
    """Returns all tests for the specified builder."""
    return self._get_tests_for([builder_id])

  def tests_triggered_by(self, builder_id):
    """Returns all tests for builders triggered by the specified builder."""
    return self._get_tests_for(self.bot_config.bot_db.bot_graph[builder_id])

  def get_compile_targets(self, tests):
    compile_targets = set()

    # Track the migration of compile_targets to source side specs
    migrated = {}
    needs_migration = {}

    for builder_id in self.bot_config.builder_ids:
      bot_spec = self.bot_config.bot_db[builder_id]

      recipe_compile_targets = set(bot_spec.compile_targets)
      compile_targets.update(recipe_compile_targets)

      source_side_spec = self._source_side_specs[builder_id.master].get(
          builder_id.builder, {})
      source_compile_targets = set(
          source_side_spec.get('additional_compile_targets', []))
      compile_targets.update(source_compile_targets)

      migrated[builder_id] = recipe_compile_targets & source_compile_targets
      needs_migration[builder_id] = (
          recipe_compile_targets - source_compile_targets)

    migrated = {k: v for k, v in migrated.iteritems() if v}
    needs_migration = {k: v for k, v in needs_migration.iteritems() if v}

    if migrated or needs_migration:

      def step_name(builder_id, targets):
        return '{}%{}%{}'.format(builder_id.master, builder_id.builder,
                                 ','.join(sorted(targets)))

      step_api = self._chromium_tests_api.m.step
      with step_api.nest('compile_targets migration') as presentation:
        presentation.step_text = (
            '\nThis is an informational step for infra maintainers')
        if migrated:
          with step_api.nest('migrated'):
            for builder_id, targets in sorted(migrated.iteritems()):
              step_api(step_name(builder_id, targets), [])
        if needs_migration:
          with step_api.nest('needs migration'):
            for builder_id, targets in sorted(needs_migration.iteritems()):
              step_api(step_name(builder_id, targets), [])

    for t in tests:
      compile_targets.update(t.compile_targets())

    return sorted(compile_targets)

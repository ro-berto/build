# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import traceback

from . import bot_db as bot_db_module
from . import steps
from . import try_spec as try_spec_module

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.attr_utils import (attrib, attrs, cached_property,
                                             mapping, sequence)


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
  _try_spec = attrib(try_spec_module.TrySpec)

  @classmethod
  def create(cls, bot_db, try_spec, python_api=None):
    """Create a BotConfig instance.

    Args:
      * bot_db - The BotDatabase containing the builders of
        try_spec.mirrors.
      * try_spec - A TrySpec instance that specifies the builders to
        mirror and any try-specific settings.
      * python_api - Optional python API. If provided, in the event that
        a BotConfigException would be raised, an infra failing step will
        be created with the details instead.

    Raises:
      * BotConfigException if there isn't configuration matching all of
        builders in try_spec.mirrors and python_api is None.
      * InfraFailure if there isn't configuration matching all of
        builders in try_spec.mirrors and python_api is not None.
    """
    try:
      return cls(bot_db, try_spec)
    except BotConfigException as e:
      if python_api is not None:
        python_api.infra_failing_step(
            str(e), [traceback.format_exc()], as_log='details')
      raise

  def __attrs_post_init__(self):
    for mirror in self.bot_mirrors:
      if not mirror.builder_id.group in self.bot_db.builders_by_group:
        raise BotConfigException(
            'No configuration present for group {!r}'.format(
                mirror.builder_id.group))
      if not mirror.builder_id in self.bot_db:
        raise BotConfigException(
            'No configuration present for builder {!r} in group {!r}'.format(
                mirror.builder_id.builder, mirror.builder_id.group))

  @cached_property
  def builder_ids(self):
    return [m.builder_id for m in self.bot_mirrors]

  @cached_property
  def mirrors(self):
    return self._try_spec.mirrors

  # TODO(gbeaty) Remove this, update code to access mirrors instead
  @cached_property
  def bot_mirrors(self):
    return self.mirrors

  # TODO(gbeaty) Remove this, update code to use the bot config directly
  @cached_property
  def settings(self):
    return self

  # TODO(gbeaty) Remove this, update code to access try_spec instead
  @cached_property
  def config(self):
    return self._try_spec

  @cached_property
  def retry_failed_shards(self):
    return self._try_spec.retry_failed_shards

  @cached_property
  def is_compile_only(self):
    return self._try_spec.execution_mode == try_spec_module.COMPILE

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

  @cached_property
  def source_side_spec_files(self):
    groups = set(key.group for key in self.all_keys)
    return {g: '{}.json'.format(g) for g in groups}

  def _get_source_side_specs(self, chromium_tests_api):
    return {
        group: chromium_tests_api.read_source_side_spec(spec_file)
        for group, spec_file in sorted(self.source_side_spec_files.iteritems())
    }

  def create_build_config(self, chromium_tests_api, bot_update_step):
    # The scripts_compile_targets is indirected through a function so that we
    # don't execute unnecessary steps if there are no scripts that need to be
    # run
    # Memoize the call to get_compile_targets_for_scripts so that we only
    # execute the step once
    memo = []

    def scripts_compile_targets_fn():
      if not memo:
        memo.append(chromium_tests_api.get_compile_targets_for_scripts())
      return memo[0]

    source_side_specs = self._get_source_side_specs(chromium_tests_api)
    tests = {}
    # migration type -> builder group -> builder -> test info
    # migration type is one of 'already migrated', 'needs migration', 'mismatch'
    # test info is a dict with key 'test' storing the name of the test and the
    # optional key 'logs' containing logs to add to the migration tracking step
    # for the test
    migration_state = {}

    for builder_id in self.all_keys:
      builder_spec = self.bot_db[builder_id]
      builder_tests, builder_migration_state = (
          chromium_tests_api.generate_tests_from_source_side_spec(
              source_side_specs[builder_id.group],
              builder_spec,
              builder_id.builder,
              builder_id.group,
              builder_spec.swarming_dimensions,
              scripts_compile_targets_fn,
              bot_update_step,
          ))
      tests[builder_id] = builder_tests

      for key, migration_tests in builder_migration_state.iteritems():
        if not migration_tests:
          continue
        migration_type_dict = migration_state.setdefault(key, {})
        group_dict = migration_type_dict.setdefault(builder_id.group, {})
        group_dict[builder_id.builder] = migration_tests

    if migration_state:
      self._report_test_spec_migration_state(chromium_tests_api,
                                             migration_state)

    return BuildConfig(self, source_side_specs, tests)

  @staticmethod
  def _report_test_spec_migration_state(chromium_tests_api, migration_state):
    with chromium_tests_api.m.step.nest('test spec migration') as presentation:
      presentation.step_text = (
          '\nThis is an informational step for infra maintainers')
      for key, groups in sorted(migration_state.iteritems()):
        with chromium_tests_api.m.step.nest(key):
          for group, builders in sorted(groups.iteritems()):
            with chromium_tests_api.m.step.nest(group):
              for builder, tests in sorted(builders.iteritems()):
                with chromium_tests_api.m.step.nest(builder):
                  for t in sorted(tests, key=lambda t: t['test']):
                    result = chromium_tests_api.m.step(t['test'], [])
                    for log, contents in sorted(t.get('logs', {}).iteritems()):
                      result.presentation.logs[log] = contents


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

  bot_config = attrib(BotConfig)
  # The values should be a mapping from builder name to the test specs
  # for the builder (mapping[str, mapping[str, ...]]), but if we enforce
  # that here, then a bad spec for one builder would cause all builders
  # that read that file to fail, so we don't apply any constraints to
  # the value here to limit the blast radius of bad changes
  _source_side_specs = attrib(mapping[str, ...])
  _tests = attrib(mapping[chromium.BuilderId, sequence[steps.Test]])

  # NOTE: All of the tests_in methods are returning mutable objects
  # (and we expect them to be mutated, e.g., to update the swarming
  # command lines to use when we determine what they are).
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

    for builder_id in self.bot_config.builder_ids:
      source_side_spec = self._source_side_specs[builder_id.group].get(
          builder_id.builder, {})
      compile_targets.update(
          source_side_spec.get('additional_compile_targets', []))

    for t in tests:
      compile_targets.update(t.compile_targets())

    return sorted(compile_targets)

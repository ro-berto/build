# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast
import collections
import copy
import sys

from recipe_engine.types import freeze

from . import bot_spec as bot_spec_module

from RECIPE_MODULES.build import chromium


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

  def __init__(self, bots_dict, builder_ids_or_bot_mirrors):
    updated_masters = {}
    for master_name, master_config in bots_dict.iteritems():
      updated_builders = {}
      builders = master_config.get('builders', {})
      for builder_name, spec in builders.iteritems():
        try:
          new_spec = bot_spec_module.BotSpec.normalize(spec)
        except Exception as e:
          # Re-raise the exception with information that identifies the builder
          # dict that is problematic
          message = '{} while creating spec for ({!r}, {!r}): {}'.format(
              e.message, master_name, builder_name, spec)
          raise type(e)(message), None, sys.exc_info()[2]
        if new_spec is not spec:
          updated_builders[builder_name] = new_spec
      if updated_builders:
        builders = dict(master_config['builders'])
        builders.update(updated_builders)
        master_config = dict(master_config)
        master_config['builders'] = builders
        updated_masters[master_name] = master_config

    if updated_masters:
      bots_dict = dict(bots_dict)
      bots_dict.update(updated_masters)
      bots_dict = freeze(bots_dict)

    self._bots_dict = bots_dict

    assert len(builder_ids_or_bot_mirrors) >= 1

    self._bot_mirrors = tuple(
        bot_spec_module.BotMirror.normalize(b)
        for b in builder_ids_or_bot_mirrors)

    for spec in self._bot_mirrors:
      m = spec.builder_id.master
      b = spec.builder_id.builder
      if not m in self._bots_dict:
        raise Exception('No configuration present for master %s' % m)
      master_dict = self._bots_dict[m]
      if not b in master_dict.get('builders', {}):
        raise Exception(
            'No configuration present for builder %s in master %s' % (b, m))

  @property
  def builder_ids(self):
    return [m.builder_id for m in self._bot_mirrors]

  @property
  def bot_mirrors(self):
    return self._bot_mirrors

  def get_bot_type(self, builder_id):
    return self._get(builder_id, 'bot_type', bot_spec_module.BUILDER_TESTER)

  def _consistent_get(self, getter, name, default=None):
    # This logic must be kept in sync with checkConsistentGet in
    # tests/masters_recipes_test.py . It's not feasible to otherwise write an
    # integration test for this code which runs against all of the bots in
    # trybots.py.
    result = getter(self.builder_ids[0], name, default)
    for builder_id in self.builder_ids:
      other_result = getter(builder_id, name, default)
      assert result == other_result, (
          'Inconsistent value for %r: bot %r has %r, '
          'but bot %r has %r' % (name, self.builder_ids[0], result, builder_id,
                                 other_result))
    return result

  def _get_builder_bot_config(self, builder_id):
    # WARNING: This doesn't take into account dynamic
    # tests from test spec etc. If you need that, please use build_config.
    return self._bots_dict.get(builder_id.master, {}).get('builders', {}).get(
        builder_id.builder, {})

  def _get(self, builder_id, name, default=None):
    return self._get_builder_bot_config(builder_id).get(name, default)

  def get(self, name, default=None):
    return self._consistent_get(self._get, name, default)

  def __getattr__(self, attr):
    per_builder_values = {}
    for builder_id in self.builder_ids:
      bot_spec = self._bots_dict[builder_id.master]['builders'][builder_id
                                                                .builder]
      value = getattr(bot_spec, attr)
      per_builder_values[builder_id] = value
    values = list(set(per_builder_values.values()))
    assert len(values) == 1, 'Inconsistent value for {!r}:\n  {}'.format(
        attr, '\n  '.join('{!r}: {!r}'.format(k, v)
                          for k, v in per_builder_values.iteritems()))
    return values[0]

  def _get_source_side_spec(self, chromium_tests_api, mastername):
    builder_ids = self.builder_ids
    if len(builder_ids) == 1:
      bot_config = self._get_builder_bot_config(builder_ids[0])

      # The official builders specify the test spec using a test_spec property
      # in the bot_config instead of reading it from a file.
      if 'source_side_spec' in bot_config:  # pragma: no cover
        return {builder_ids[0].builder: bot_config['source_side_spec']}

      # Similar to the source_side_spec special case above, but expected to
      # contain the spec for every builder on the waterfall. This is necessary
      # because only having one builder like in the source_side_spec approach
      # breaks parent/child builder relationships due to the parent not knowing
      # which targets to build and isolate for its children.
      elif 'downstream_spec' in bot_config:  # pragma: no cover
        return bot_config['downstream_spec']

    # TODO(phajdan.jr): Get rid of disable_tests.
    if self.get('disable_tests'):
      return {}

    source_side_spec_file = self.get('testing', {}).get('source_side_spec_file',
                                                        '%s.json' % mastername)

    return chromium_tests_api.read_source_side_spec(source_side_spec_file)

  def create_build_config(self, chromium_tests_api, bot_update_step):
    # TODO(phajdan.jr): Get rid of disable_tests.
    if self.get('disable_tests'):
      scripts_compile_targets = {}
    else:
      scripts_compile_targets = \
          chromium_tests_api.get_compile_targets_for_scripts(self)

    def is_child_of(builder_config, parent_mastername, parent_buildername):
      return (parent_mastername == builder_config.get('parent_mastername') and
              parent_buildername == builder_config.get('parent_buildername'))

    masternames = set()
    for builder_id in self.builder_ids:
      bot_master_name = builder_id.master
      bot_builder_name = builder_id.builder
      masternames.add(bot_master_name)

      for master_name, master_config in self._bots_dict.iteritems():
        if master_name == bot_master_name:
          continue

        if any(
            is_child_of(b, bot_master_name, bot_builder_name)
            for b in master_config.get('builders', {}).itervalues()):
          masternames.add(master_name)

    db = {}

    for mastername in sorted(self._bots_dict):
      # We manually thaw the path to the elements we are modifying, since the
      # builders are frozen.
      master_dict = dict(self._bots_dict[mastername])

      if mastername in masternames:
        source_side_spec = self._get_source_side_spec(chromium_tests_api,
                                                      mastername)

        builders = master_dict['builders'] = dict(master_dict['builders'])
        for loop_buildername in builders:
          builder_dict = builders[loop_buildername] = (
              dict(builders[loop_buildername]))
          builders[loop_buildername]['tests'] = (
              chromium_tests_api.generate_tests_from_source_side_spec(
                  source_side_spec,
                  builder_dict,
                  loop_buildername,
                  mastername,
                  builder_dict.get('swarming_dimensions', {}),
                  scripts_compile_targets,
                  bot_update_step,
              ))
      else:
        source_side_spec = None

      db[mastername] = {
          'master_dict': freeze(master_dict),
          'source_side_spec': source_side_spec,
      }

    return BuildConfig(self._bot_mirrors, db)

  # TODO(gbeaty) Move to BuildConfig
  # TODO(gbeaty) Remove unnecessary chromium_tests_api parameter
  def get_compile_targets(self, chromium_tests_api, build_config, tests):
    compile_targets = set()
    for builder_id in self.builder_ids:
      bot_config = build_config.get_bot_config(builder_id)
      compile_targets.update(bot_config.get('compile_targets', []))
      compile_targets.update(
          build_config.get_source_side_spec(builder_id).get(
              'additional_compile_targets', []))

    if self.get('add_tests_as_compile_targets', True):
      for t in tests:
        compile_targets.update(t.compile_targets())

    return sorted(compile_targets)


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

  class _ConfigNode(object):
    """A node in the builder graph.

    Corresponds to an individual builder.
    """

    def __init__(self, builder_id, mirrored, tests):
      self.children = {}
      # A BuilderId that uniquely identifies this builder.
      self.builder_id = builder_id
      # Whether this builder should be mirrored by trybots based on
      # the bot IDs provided to _TestConfig.__init__.
      self.mirrored = mirrored
      # This builder's tests.
      self.tests = tests

  def __init__(self, bot_mirrors, db):
    # Indexed by mastername. Each entry contains a master_dict and a
    # source_side_spec.
    self._db = freeze(db)
    self._config = self._ConfigNode(None, False, None)

    for mirror in bot_mirrors:
      builder_bot_config = self.get_bot_config(mirror.builder_id)
      if mirror.builder_id not in self._config.children:
        self._config.children[mirror.builder_id] = self._ConfigNode(
            mirror.builder_id, True, builder_bot_config.get('tests', []))
      builder_config = self._config.children[mirror.builder_id]

      if mirror.tester_id:
        tester_bot_config = self.get_bot_config(mirror.tester_id)
        builder_config.children[mirror.tester_id] = self._ConfigNode(
            mirror.tester_id, True, tester_bot_config.get('tests', []))

      for (
          _luci_project, triggered_mastername, triggered_buildername,
          triggered_bot_config) in self.bot_configs_matching_parent_buildername(
              mirror.builder_id):
        triggered_id = chromium.BuilderId.create_for_master(
            triggered_mastername, triggered_buildername)
        if triggered_id not in builder_config.children:
          builder_config.children[triggered_id] = self._ConfigNode(
              triggered_id, False, triggered_bot_config.get('tests', []))

  # TODO(gbeaty) Move this method, it's not rev-specific information
  def get_bot_config(self, builder_id):
    return self._db[builder_id.master]['master_dict'].get('builders', {}).get(
        builder_id.builder)

  # TODO(gbeaty) Move this method, it's not rev-specific information
  def get_master_settings(self, mastername):
    return self._db[mastername]['master_dict'].get('settings', {})

  # TODO(gbeaty) Move this method, it's not rev-specific information
  def bot_configs_matching_parent_buildername(self, parent_builder_id):
    """A generator of all the (buildername, bot_config) tuples whose
    parent_buildername is the passed one on the given master.
    """
    for mastername, master_config in self._db.iteritems():
      builders = master_config['master_dict'].get('builders', {})
      for buildername, bot_config in builders.iteritems():
        parent_mastername = bot_config.get('parent_mastername', mastername)
        parent_buildername = bot_config.get('parent_buildername')
        if (parent_builder_id.master == parent_mastername and
            parent_builder_id.builder == parent_buildername):
          master_settings = self.get_master_settings(mastername)
          luci_project = master_settings.get('luci_project', 'chromium')
          yield luci_project, mastername, buildername, bot_config

  def get_source_side_spec(self, builder_id):
    return self._db[builder_id.master]['source_side_spec'].get(
        builder_id.builder, {})

  def all_tests(self):
    """Returns all tests."""
    return list(self._iter_tests(node for node, _ in self._iter_nodes()))

  def tests_in_scope(self):
    """Returns all tests for the provided bot IDs."""
    return list(
        self._iter_tests(
            node for node, _ in self._iter_nodes() if node.mirrored))

  def tests_on(self, builder_id):
    """Returns all tests for the specified builder."""
    return list(
        self._iter_tests(node for node, _ in self._iter_nodes()
                         if builder_id == node.builder_id))

  def tests_triggered_by(self, builder_id):
    """Returns all tests for builders triggered by the specified builder."""
    return list(
        self._iter_tests(node for node, parent in self._iter_nodes()
                         if parent and builder_id == parent.builder_id))

  def _iter_nodes(self):
    """Generates a sequence of node pairs from the builder graph.

    Each pair is (node, parent).
    """

    def _iter_nodes_impl(node, parent_node):
      yield (node, parent_node)

      for val in node.children.itervalues():
        for node_pair in _iter_nodes_impl(val, node):
          yield node_pair

    for node, parent_node in _iter_nodes_impl(self._config, None):
      yield (node, parent_node)

  def _iter_tests(self, nodes):
    """Generates a sequence of tests contained in the given nodes.

    Args:
      nodes: an iterable of _ConfigNodes.
    """
    for node in nodes:
      for test in node.tests or []:
        yield test

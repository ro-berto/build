# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast
import collections
import copy

from recipe_engine.types import freeze

from . import bot_spec


MB_CONFIG_FILENAME = ['tools', 'mb', 'mb_config.pyl']


class BotConfig(object):
  """Wrapper that allows combining several compatible bot configs."""

  def __init__(self, bots_dict, bot_ids):
    self._bots_dict = bots_dict

    assert len(bot_ids) >= 1

    def normalize(bot_id):
      if not isinstance(bot_id, BotConfig.BotId):
        bot_id = BotConfig.BotId(**bot_id)
      return bot_id

    self._bot_ids = tuple(normalize(b) for b in bot_ids)

    for bot_id in self._bot_ids:
      m = bot_id.mastername
      b = bot_id.buildername
      if not m in self._bots_dict:
        raise Exception('No configuration present for master %s' % m)
      master_dict = self._bots_dict[m]
      if not b in master_dict.get('builders', {}):
        raise Exception(
            'No configuration present for builder %s in master %s' % (b, m))

  class BotId(collections.namedtuple('BotId',
                                     ('mastername', 'buildername', 'tester',
                                      'tester_mastername'))):

    __slots__ = ()

    def __new__(cls, mastername, buildername, tester=None,
                tester_mastername=None):
      tester_mastername = tester_mastername or mastername if tester else None
      return super(BotConfig.BotId, cls).__new__(
          cls, mastername, buildername, tester, tester_mastername)

  @property
  def bot_ids(self):
    return self._bot_ids

  def get_bot_type(self, bot_id):
    return self._get(bot_id, 'bot_type', bot_spec.BUILDER_TESTER)

  def _consistent_get(self, getter, name, default=None):
    # This logic must be kept in sync with checkConsistentGet in
    # tests/masters_recipes_test.py . It's not feasible to otherwise write an
    # integration test for this code which runs against all of the bots in
    # trybots.py.
    result = getter(self._bot_ids[0], name, default)
    for bot_id in self._bot_ids:
      other_result = getter(bot_id, name, default)
      assert result == other_result, (
          'Inconsistent value for %r: bot %r has %r, '
          'but bot %r has %r' % (
              name, self._bot_ids[0], result, bot_id, other_result))
    return result

  def _get_builder_bot_config(self, bot_id):
    # WARNING: This doesn't take into account dynamic
    # tests from test spec etc. If you need that, please use bot_db.
    return self._bots_dict.get(bot_id.mastername, {}).get(
        'builders', {}).get(bot_id.buildername, {})

  def _get(self, bot_id, name, default=None):
    return self._get_builder_bot_config(bot_id).get(name, default)

  def get(self, name, default=None):
    return self._consistent_get(self._get, name, default)

  def _get_source_side_spec(self, chromium_tests_api, mastername):
    if len(self._bot_ids) == 1:
      bot_config = self._get_builder_bot_config(self._bot_ids[0])

      # The official builders specify the test spec using a test_spec property
      # in the bot_config instead of reading it from a file.
      if 'source_side_spec' in bot_config: # pragma: no cover
        return { self._bot_ids[0].buildername: bot_config['source_side_spec'] }

      # Similar to the source_side_spec special case above, but expected to
      # contain the spec for every builder on the waterfall. This is necessary
      # because only having one builder like in the source_side_spec approach
      # breaks parent/child builder relationships due to the parent not knowing
      # which targets to build and isolate for its children.
      elif 'downstream_spec' in bot_config: # pragma: no cover
        return bot_config['downstream_spec']

    # TODO(phajdan.jr): Get rid of disable_tests.
    if self.get('disable_tests'):
      return {}

    source_side_spec_file = self.get('testing', {}).get(
        'source_side_spec_file', '%s.json' % mastername)

    return chromium_tests_api.read_source_side_spec(source_side_spec_file)

  def initialize_bot_db(self, chromium_tests_api, bot_db, bot_update_step):
    # TODO(phajdan.jr): Get rid of disable_tests.
    if self.get('disable_tests'):
      scripts_compile_targets = {}
    else:
      scripts_compile_targets = \
          chromium_tests_api.get_compile_targets_for_scripts(self)

    def is_child_of(builder_config, parent_mastername, parent_buildername):
      return (
          parent_mastername == builder_config.get('parent_mastername')
          and parent_buildername == builder_config.get('parent_buildername'))

    masternames = set()
    for bot_id in self._bot_ids:
      bot_master_name = bot_id.mastername
      bot_builder_name = bot_id.buildername
      masternames.add(bot_master_name)

      for master_name, master_config in self._bots_dict.iteritems():
        if master_name == bot_master_name:
          continue

        if any(is_child_of(b, bot_master_name, bot_builder_name)
               for b in master_config.get('builders', {}).itervalues()):
          masternames.add(master_name)

    for mastername in sorted(self._bots_dict):
      # We manually thaw the path to the elements we are modifying, since the
      # builders are frozen.
      master_dict = dict(self._bots_dict[mastername])

      if mastername in masternames:
        source_side_spec = self._get_source_side_spec(
            chromium_tests_api, mastername)

        builders = master_dict['builders'] = dict(master_dict['builders'])
        for loop_buildername in builders:
          builder_dict = builders[loop_buildername] = (
              dict(builders[loop_buildername]))
          builders[loop_buildername]['tests'] = (
              chromium_tests_api.generate_tests_from_source_side_spec(
                  source_side_spec, builder_dict,
                  loop_buildername, mastername,
                  builder_dict.get('swarming_dimensions', {}),
                  scripts_compile_targets,
                  bot_update_step,
              ))
      else:
        source_side_spec = None

      bot_db._add_master_dict_and_source_side_spec(
          mastername, freeze(master_dict), freeze(source_side_spec))

  def get_tests(self, bot_db):
    return _TestConfig(self._bot_ids, bot_db)

  def get_compile_targets(self, chromium_tests_api, bot_db, tests):
    compile_targets = set()
    for bot_id in self._bot_ids:
      bot_config = bot_db.get_bot_config(
          bot_id.mastername, bot_id.buildername)
      compile_targets.update(bot_config.get('compile_targets', []))
      compile_targets.update(bot_db.get_source_side_spec(
          bot_id.mastername, bot_id.buildername).get(
              'additional_compile_targets', []))

    if self.get('add_tests_as_compile_targets', True):
      for t in tests:
        compile_targets.update(t.compile_targets())

    return sorted(compile_targets)

  def matches_any_bot_id(self, fun):
    return any(fun(bot_id) for bot_id in self._bot_ids)


class _TestConfig(object):
  """Determines and stores tests for a given group of bots."""

  class _ConfigNode(object):
    """A node in the builder graph.

    Corresponds to an individual builder.
    """
    def __init__(self, key, mirrored, tests):
      self.children = {}
      # A key that uniquely identifies this builder.
      # Currently (mastername, buildername)
      self.key = key
      # Whether this builder should be mirrored by trybots based on
      # the bot IDs provided to _TestConfig.__init__.
      self.mirrored = mirrored
      # This builder's tests.
      self.tests = tests

  def __init__(self, bot_ids, bot_db):
    """Creates a _TestConfig instance.

    This creates a directed acyclic builder graph, with the builders
    described by the provided bot IDs as the root nodes and the builders
    they trigger as their children. Nodes keep track of whether they're
    referenced by a bot ID (and would thus be mirrored by trybots).
    """
    self._config = self._ConfigNode(None, False, None)

    for bot_id in bot_ids:
      builder_bot_config = bot_db.get_bot_config(
          bot_id.mastername, bot_id.buildername)
      key = bot_id.mastername, bot_id.buildername
      if key not in self._config.children:
        self._config.children[key] = self._ConfigNode(
            key, True, builder_bot_config.get('tests', []))
      builder_config = self._config.children[key]

      if bot_id.tester:
        tester_bot_config = bot_db.get_bot_config(
            bot_id.tester_mastername, bot_id.tester)
        tester_key = bot_id.tester_mastername, bot_id.tester
        builder_config.children[tester_key] = self._ConfigNode(
            tester_key, True, tester_bot_config.get('tests', []))

      for (
            _luci_project,
            triggered_mastername,
            triggered_buildername,
            triggered_bot_config
          ) in bot_db.bot_configs_matching_parent_buildername(
              bot_id.mastername, bot_id.buildername):
        triggered_key = (triggered_mastername, triggered_buildername)
        if triggered_key not in builder_config.children:
          builder_config.children[triggered_key] = self._ConfigNode(
              triggered_key, False, triggered_bot_config.get('tests', []))

  def all_tests(self):
    """Returns all tests."""
    return list(self._iter_tests(
        node for node, _ in self._iter_nodes()))

  def tests_in_scope(self):
    """Returns all tests for the provided bot IDs."""
    return list(self._iter_tests(
        node for node, _ in self._iter_nodes()
        if node.mirrored))

  def tests_on(self, mastername, buildername):
    """Returns all tests for the specified builder."""
    return list(self._iter_tests(
        node for node, _ in self._iter_nodes()
        if (mastername, buildername) == node.key))

  def tests_triggered_by(self, mastername, buildername):
    """Returns all tests for builders triggered by the specified builder."""
    return list(self._iter_tests(
        node for node, parent in self._iter_nodes()
        if parent and (mastername, buildername) == parent.key))

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


class BotConfigAndTestDB(object):
  """An immutable database of bot configurations and test specifications.
  Holds the data for potentially multiple waterfalls (masternames). Most
  queries against this database are made with (mastername, buildername)
  pairs.
  """

  def __init__(self):
    # Indexed by mastername. Each entry contains a master_dict and a
    # source_side_spec.
    self._db = {}

  def _add_master_dict_and_source_side_spec(
      self, mastername, master_dict, source_side_spec):
    """Only used during construction in chromium_tests.prepare_checkout. Do not
    call this externally.
    """
    # TODO(kbr): currently the master_dicts that are created by
    # get_master_dict_with_dynamic_tests are over-specialized to a
    # particular builder. This needs to be fixed so that there's exactly
    # one master_dict per waterfall.
    assert mastername not in self._db, (
        'Illegal attempt to add multiple master dictionaries for waterfall %s' %
        (mastername))
    self._db[mastername] = { 'master_dict': master_dict,
                             'source_side_spec': source_side_spec }

  def get_bot_config(self, mastername, buildername):
    return self._db[mastername]['master_dict'].get('builders', {}).get(
        buildername)

  def get_master_settings(self, mastername):
    return self._db[mastername]['master_dict'].get('settings', {})

  def bot_configs_matching_parent_buildername(
      self, parent_mastername, parent_buildername):
    """A generator of all the (buildername, bot_config) tuples whose
    parent_buildername is the passed one on the given master.
    """
    for mastername, master_config in self._db.iteritems():
      master_dict = master_config['master_dict']
      for buildername, bot_config in master_dict.get(
          'builders', {}).iteritems():
        master_matches = (bot_config.get('parent_mastername', mastername) ==
                          parent_mastername)
        builder_matches = (bot_config.get('parent_buildername') ==
                           parent_buildername)
        if master_matches and builder_matches:
          master_settings = self.get_master_settings(mastername)
          luci_project = master_settings.get('luci_project', 'chromium')
          yield luci_project, mastername, buildername, bot_config

  def get_source_side_spec(self, mastername, buildername):
    return self._db[mastername]['source_side_spec'].get(buildername, {})

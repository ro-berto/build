# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast
import copy

from recipe_engine.types import freeze


MB_CONFIG_FILENAME = ['tools', 'mb', 'mb_config.pyl']


class BotConfig(object):
  """Wrapper that allows combining several compatible bot configs."""

  def __init__(self, bots_dict, bot_ids):
    self._bots_dict = bots_dict

    assert len(bot_ids) >= 1
    self._bot_ids = bot_ids

    for bot_id in self._bot_ids:
      m = bot_id['mastername']
      b = bot_id['buildername']
      if not m in self._bots_dict:
        raise Exception('No configuration present for master %s' % m)
      master_dict = self._bots_dict[m]
      if not b in master_dict.get('builders', {}):
        raise Exception('No configuration present for builder %s in master %s' % (b, m))

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
    return self._bots_dict.get(bot_id['mastername'], {}).get(
        'builders', {}).get(bot_id['buildername'], {})

  def _get(self, bot_id, name, default=None):
    return self._get_builder_bot_config(bot_id).get(name, default)

  def get(self, name, default=None):
    return self._consistent_get(self._get, name, default)

  def _get_master_setting(self, bot_id, name, default=None):
    return self._bots_dict.get(bot_id['mastername'], {}).get(
        'settings', {}).get(name, default)

  def get_master_setting(self, name, default=None):
    return self._consistent_get(self._get_master_setting, name, default)

  def _get_test_spec(self, chromium_tests_api, mastername):
    if len(self._bot_ids) == 1:
      bot_config = self._get_builder_bot_config(self._bot_ids[0])

      # The official builders specify the test spec using a test_spec property in
      # the bot_config instead of reading it from a file.
      if 'test_spec' in bot_config: # pragma: no cover
        return { self._bot_ids[0]['buildername']: bot_config['test_spec'] }


    test_spec_file = self.get('testing', {}).get(
        'test_spec_file', '%s.json' % mastername)

    # TODO(phajdan.jr): Get rid of disable_tests.
    if self.get('disable_tests'):
      return {}
    return chromium_tests_api.read_test_spec(test_spec_file)

  def initialize_bot_db(self, chromium_tests_api, bot_db, bot_update_step):
    # TODO(phajdan.jr): Get rid of disable_tests.
    if self.get('disable_tests'):
      scripts_compile_targets = {}
    else:
      scripts_compile_targets = \
          chromium_tests_api.get_compile_targets_for_scripts(self)

    # chromium_tests_api.steps.generate_isolated_script should be in front.
    # because this lets webkit_layout_tests runs later and bot's s resources
    # are utilized by receiving result of other tests while webkit_layout_tests
    # is running.
    test_generators = [
      chromium_tests_api.steps.generate_isolated_script,
      chromium_tests_api.steps.generate_cts_test,
      chromium_tests_api.steps.generate_gtest,
      chromium_tests_api.steps.generate_instrumentation_test,
      chromium_tests_api.steps.generate_junit_test,
      chromium_tests_api.steps.generate_script,
    ]

    masternames = set(bot_id['mastername'] for bot_id in self._bot_ids)
    for mastername in sorted(self._bots_dict):
      # We manually thaw the path to the elements we are modifying, since the
      # builders are frozen.
      master_dict = dict(self._bots_dict[mastername])

      if mastername in masternames:
        test_spec = self._get_test_spec(chromium_tests_api, mastername)

        builders = master_dict['builders'] = dict(master_dict['builders'])
        for loop_buildername in builders:
          builder_dict = builders[loop_buildername] = (
              dict(builders[loop_buildername]))
          builders[loop_buildername]['tests'] = (
              chromium_tests_api.generate_tests_from_test_spec(
                  test_spec, builder_dict,
                  loop_buildername, mastername,
                  builder_dict.get('swarming_dimensions', {}),
                  scripts_compile_targets,
                  test_generators,
                  bot_update_step,
                  self
              ))
      else:
        test_spec = None


      bot_db._add_master_dict_and_test_spec(
          mastername, freeze(master_dict), freeze(test_spec))

  def get_tests(self, bot_db):
    tests = []
    for bot_id in self._bot_ids:
      bot_config = bot_db.get_bot_config(
          bot_id['mastername'], bot_id['buildername'])
      tests.extend([copy.deepcopy(t) for t in bot_config.get('tests', [])])

      if bot_id.get('tester'):
        bot_config = bot_db.get_bot_config(
            bot_id['mastername'], bot_id['tester'])
        tests.extend([copy.deepcopy(t) for t in bot_config.get('tests', [])])

    tests_including_triggered = list(tests)
    for bot_id in self._bot_ids:
      for _, _, _, test_bot in bot_db.bot_configs_matching_parent_buildername(
          bot_id['mastername'], bot_id['buildername']):
        tests_including_triggered.extend(test_bot.get('tests', []))

    return tests, tests_including_triggered

  def get_compile_targets(self, chromium_tests_api, bot_db, tests):
    compile_targets = set()
    for bot_id in self._bot_ids:
      bot_config = bot_db.get_bot_config(
          bot_id['mastername'], bot_id['buildername'])
      compile_targets.update(set(bot_config.get('compile_targets', [])))
      compile_targets.update(bot_db.get_test_spec(
          bot_id['mastername'], bot_id['buildername']).get(
              'additional_compile_targets', []))

    if self.get('add_tests_as_compile_targets', True):
      for t in tests:
        compile_targets.update(t.compile_targets(chromium_tests_api.m))

    return sorted(compile_targets)

  def matches_any_bot_id(self, fun):
    return any(fun(bot_id) for bot_id in self._bot_ids)


class BotConfigAndTestDB(object):
  """An immutable database of bot configurations and test specifications.
  Holds the data for potentially multiple waterfalls (masternames). Most
  queries against this database are made with (mastername, buildername)
  pairs.
  """

  def __init__(self):
    # Indexed by mastername. Each entry contains a master_dict and a
    # test_spec.
    self._db = {}

  def _add_master_dict_and_test_spec(self, mastername, master_dict, test_spec):
    """Only used during construction in chromium_tests.prepare_checkout. Do not
    call this externally.
    """
    # TODO(kbr): currently the master_dicts that are created by
    # get_master_dict_with_dynamic_tests are over-specialized to a
    # particular builder -- the "enable_swarming" flag paradoxically comes
    # from that builder, rather than from each individual builder and/or
    # the parent builder. This needs to be fixed so that there's exactly
    # one master_dict per waterfall.
    assert mastername not in self._db, (
        'Illegal attempt to add multiple master dictionaries for waterfall %s' %
        (mastername))
    self._db[mastername] = { 'master_dict': master_dict,
                             'test_spec': test_spec }

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

  def get_test_spec(self, mastername, buildername):
    return self._db[mastername]['test_spec'].get(buildername, {})

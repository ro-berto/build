# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze


class BotConfig(object):
  """Wrapper that allows combining several compatible bot configs."""

  def __init__(self, bots_dict, bot_ids):
    self._bots_dict = bots_dict

    assert len(bot_ids) >= 1
    self._bot_ids = bot_ids

  def _consistent_get(self, getter, name, default=None):
    result = getter(self._bot_ids[0], name, default)
    for bot_id in self._bot_ids:
      other_result = getter(bot_id, name, default)
      assert result == other_result, (
          'Inconsistent value for %r: bot %r has %r, '
          'but bot %r has %r' % (
              name, self._bot_ids[0], result, bot_id, other_result))
    return result

  def _get_bot_config(self, bot_id):
    return self._bots_dict.get(bot_id['mastername'], {}).get(
        'builders', {}).get(bot_id['buildername'], {})

  def _get(self, bot_id, name, default=None):
    return self._get_bot_config(bot_id).get(name, default)

  def get(self, name, default=None):
    return self._consistent_get(self._get, name, default)

  def _get_master_setting(self, bot_id, name, default=None):
    return self._bots_dict.get(bot_id['mastername'], {}).get(
        'settings', {}).get(name, default)

  def get_master_setting(self, name, default=None):
    return self._consistent_get(self._get_master_setting, name, default)

  def _get_test_spec(self, chromium_tests_api):
    # TODO(phajdan.jr): Make test specs work for more than 1 bot.
    assert len(self._bot_ids) == 1

    bot_config = self._get_bot_config(self._bot_ids[0])
    mastername = self._bot_ids[0]['mastername']
    buildername = self._bot_ids[0]['buildername']

    # The official builders specify the test spec using a test_spec property in
    # the bot_config instead of reading it from a file.
    if 'test_spec' in bot_config:
      return { buildername: bot_config['test_spec'] }

    test_spec_file = bot_config.get('testing', {}).get(
        'test_spec_file', '%s.json' % mastername)

    # TODO(phajdan.jr): Bots should have no generators instead.
    if bot_config.get('disable_tests'):
      return {}
    return chromium_tests_api.read_test_spec(chromium_tests_api.m, test_spec_file)

  def initialize_bot_db(self, chromium_tests_api, bot_db):
    # TODO(phajdan.jr): Make this work for more than 1 bot.
    assert len(self._bot_ids) == 1

    bot_config = self._get_bot_config(self._bot_ids[0])
    mastername = self._bot_ids[0]['mastername']
    buildername = self._bot_ids[0]['buildername']

    test_spec = self._get_test_spec(chromium_tests_api)

    # TODO(phajdan.jr): Bots should have no generators instead.
    if bot_config.get('disable_tests'):
      scripts_compile_targets = {}
    else:
      scripts_compile_targets = \
          chromium_tests_api.get_compile_targets_for_scripts().json.output

    # We manually thaw the path to the elements we are modifying, since the
    # builders are frozen.
    master_dict = dict(self._bots_dict[mastername])
    builders = master_dict['builders'] = dict(master_dict['builders'])
    bot_config = builders[buildername]
    for loop_buildername in builders:
      builder_dict = builders[loop_buildername] = (
          dict(builders[loop_buildername]))
      builders[loop_buildername]['tests'] = (
          chromium_tests_api.generate_tests_from_test_spec(
              chromium_tests_api.m, test_spec, builder_dict,
              loop_buildername, mastername,
              # TODO(phajdan.jr): Get enable_swarming value from builder_dict.
              # Above should remove the need to get bot_config and buildername
              # in this method.
              bot_config.get('enable_swarming', False),
              scripts_compile_targets, builder_dict.get('test_generators', [])
          ))

    bot_db._add_master_dict_and_test_spec(
        mastername, freeze(master_dict), freeze(test_spec))


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
      self, mastername, parent_buildername):
    """A generator of all the (buildername, bot_config) tuples whose
    parent_buildername is the passed one on the given master.
    """
    for buildername, bot_config in self._db[mastername]['master_dict'].get(
        'builders', {}).iteritems():
      if bot_config.get('parent_buildername') == parent_buildername:
        yield buildername, bot_config

  def get_test_spec(self, mastername, buildername):
    return self._db[mastername]['test_spec'].get(buildername, {})

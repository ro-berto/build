# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


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

  def _get(self, bot_id, name, default=None):
    return self._bots_dict.get(bot_id['mastername'], {}).get(
        'builders', {}).get(bot_id['buildername'], {}).get(name, default)

  def get(self, name, default=None):
    return self._consistent_get(self._get, name, default)

  def _get_master_setting(self, bot_id, name, default=None):
    return self._bots_dict.get(bot_id['mastername'], {}).get(
        'settings', {}).get(name, default)

  def get_master_setting(self, name, default=None):
    return self._consistent_get(self._get_master_setting, name, default)


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

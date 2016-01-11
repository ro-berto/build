# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

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

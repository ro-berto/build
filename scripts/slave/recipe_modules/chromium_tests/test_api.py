# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from . import bot_config_and_test_db as bdb_module
from . import builders
from . import steps
from . import trybots


class ChromiumTestsApi(recipe_test_api.RecipeTestApi):
  @property
  def builders(self):
    return builders.BUILDERS

  @property
  def steps(self):
    return steps

  @property
  def trybots(self):
    return trybots.TRYBOTS

  def platform(self, bot_ids):
    bot_config= bdb_module.BotConfig(self.builders, bot_ids)
    # TODO(phajdan.jr): Get the bitness from actual config for that bot.
    return self.m.platform(
        bot_config.get('testing', {}).get('platform'),
        bot_config.get(
            'chromium_config_kwargs', {}).get('TARGET_BITS', 64))

  @staticmethod
  def bot_config(
      builder_dict,
      mastername='test_mastername',
      buildername='test_buildername'):
    """Returns a synthesized BotConfig instance based on |builder_dict|.

    This makes it possible to test APIs taking a bot config without
    referencing production data.
    """
    return bdb_module.BotConfig(
        {mastername: {'builders': {buildername: builder_dict}}},
        [{'mastername': mastername, 'buildername': buildername}])

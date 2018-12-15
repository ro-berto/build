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

  @recipe_test_api.mod_test_data
  @staticmethod
  def handle_bot_config_errors(handle_bot_config_errors):
    """Returns a TestData that controls handling BotConfig errors.

    If BotConfig errors are handled, then any exceptions raised when creating a
    BotConfig will result in the creation of a failing step. If BotConfig errors
    are not handled, the exception will instead be propagated, allowing tests to
    fail in the event of a bad configuration.
    """
    return handle_bot_config_errors

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

  def read_source_side_spec(self, mastername, contents, step_prefix=None,
                            step_suffix=None, path_base=None):
    """Adds step data overrides for when a test reads source side test specs.

    Args:
      * mastername: The mastername the test is using (ex. 'chromium.win').
      * contents: The contents of the source side spec file.
      * step_prefix: Any prefix to add to the step name. Useful if using step
        nesting.
      * step_suffix: Any suffix to append to the step name. Useful if the step
        runs twice.
      * path_base: The path where the spec files live. If not set, defaults to
        self.m.path['checkout'].join('testing', 'buildbot')

    Returns:
      A recipe test object.
    """
    # Used to be called test specs, name has stuck around for now.
    filename = '%s.json' % mastername

    if not path_base:
      path_base = self.m.path['checkout'].join('testing', 'buildbot')

    return (
        self.override_step_data(
            '%sread test spec (%s)%s' % (
                step_prefix or '', filename, step_suffix or ''),
            self.m.json.output(contents))
    )


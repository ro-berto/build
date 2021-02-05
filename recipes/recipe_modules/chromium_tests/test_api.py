# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from . import bot_config as bot_config_module
from . import bot_db
from . import builders as builders_module
from . import try_spec


class ChromiumTestsApi(recipe_test_api.RecipeTestApi):

  @recipe_test_api.mod_test_data
  @staticmethod
  def builders(builders):
    """Override chromium_tests's builders for a test.

    Args:
      builders - A BotDatabase to replace chromium_tests.builders.
    """
    assert isinstance(builders, bot_db.BotDatabase)
    return builders

  @recipe_test_api.mod_test_data
  @staticmethod
  def trybots(trybots):
    """Override chromium_tests's builders for a test.

    Args:
      trybots - A TryDatabase to replace chromium_tests.trybots.
    """
    assert isinstance(trybots, try_spec.TryDatabase)
    return trybots

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

  @recipe_test_api.mod_test_data
  @staticmethod
  def change_size_limit(size_limit):
    """Returns an integer that limits test failure format size.

       This controls how many test failures are listed in the
       the string returned from _format_unrecoverable_failures()
    """
    return size_limit

  def platform(self, bot_mirrors):
    bot_config = bot_config_module.BotConfig.create(builders_module.BUILDERS,
                                                    bot_mirrors)
    # TODO(phajdan.jr): Get the bitness from actual config for that bot.
    return self.m.platform(
        bot_config.simulation_platform,
        bot_config.chromium_config_kwargs.get('TARGET_BITS', 64))

  def read_source_side_spec(self,
                            builder_group,
                            contents,
                            step_prefix=None,
                            step_suffix=None):
    """Adds step data overrides for when a test reads source side test specs.

    Args:
      * builder_group: The group the test is using (ex. 'chromium.win').
      * contents: The contents of the source side spec file.
      * step_prefix: Any prefix to add to the step name. Useful if using step
        nesting.
      * step_suffix: Any suffix to append to the step name. Useful if the step
        runs twice.

    Returns:
      A recipe test object.
    """
    # Used to be called test specs, name has stuck around for now.
    filename = '%s.json' % builder_group

    return (
        self.override_step_data(
            '%sread test spec (%s)%s' % (
                step_prefix or '', filename, step_suffix or ''),
            self.m.json.output(contents))
    )

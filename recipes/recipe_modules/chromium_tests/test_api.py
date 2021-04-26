# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class ChromiumTestsApi(recipe_test_api.RecipeTestApi):

  @recipe_test_api.mod_test_data
  @staticmethod
  def change_size_limit(size_limit):
    """Returns an integer that limits test failure format size.

       This controls how many test failures are listed in the
       the string returned from _format_unrecoverable_failures()
    """
    return size_limit

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

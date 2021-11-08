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

  def gen_swarming_and_rdb_results(self,
                                   suite_name,
                                   suffix,
                                   invalid=False,
                                   failures=None):
    """Adds overrides for the swarming-collect and rdb-query steps of a test.

    To mock a swarming test's results, step data needs to be provided for the
    `swarming collect` command, as well as the `rdb query` command. This helper
    method can handle all that with less boilerplate.

    Note: when not overridden, a swarming test's results by default will be
    valid with zero failures. Consequently this method only needs to be invoked
    when simulating failures.

    Args:
      suite_name: Name of the suite.
      suffix: Phase of the build the test is in (eg "with patch").
      invalid: If True, marks the results as invalid.
      failures: List of names of test cases that failed.
    """
    failures = failures if failures else []
    swarming_step_name = suite_name
    if suffix:
      swarming_step_name += ' (%s)' % suffix
    rdb_step_name = 'collect tasks'
    if suffix:
      rdb_step_name += ' (%s)' % suffix
    rdb_step_name += '.%s results' % suite_name
    return self.override_step_data(
        swarming_step_name,
        self.m.chromium_swarming.canned_summary_output(
            self.m.json.output({}), failure=invalid or
            failures)) + self.override_step_data(
                rdb_step_name,
                stdout=self.m.raw_io.output_text(
                    self.m.test_utils.rdb_results(
                        suite_name, failing_tests=failures)))

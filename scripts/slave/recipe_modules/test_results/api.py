# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class TestResultsApi(recipe_api.RecipeApi):
  """Recipe module to upload gtest json results to test-results server."""

  def upload(self, gtest_results_file, test_type, chrome_revision,
             test_results_server=None, downgrade_error_to_warning=True):
    """Upload gtest results json to test-results.

    Args:
      gtest_results_file: Path to file containing gtest json.
      test_type: Test type string, e.g. webkit_tests.
      test_results_server: Server where results should be uploaded.
      downgrade_error_to_warning: If True, treat a failure to upload as a
          warning.

    Returns:
      The step result.
    """
    try:
      return self.m.python(
          name='Upload to test-results [%s]' % test_type,
          script=self.resource('upload_gtest_test_results.py'),
          args=['--input-gtest-json', gtest_results_file,
                '--master-name', self.m.properties['mastername'],
                '--builder-name', self.m.properties['buildername'],
                '--build-number', self.m.properties['buildnumber'],
                '--test-type', test_type,
                '--test-results-server',
                test_results_server or self.c.test_results_server,
                '--chrome-revision', chrome_revision])
    except self.m.step.StepFailure as f:
      if downgrade_error_to_warning:
        f.result.presentation.status = self.m.step.WARNING
      return f.result

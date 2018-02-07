# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class TestResultsApi(recipe_api.RecipeApi):
  """Recipe module to upload gtest json results to test-results server."""

  def initialize(self):
    """Set the default config."""
    if self.m.runtime.is_experimental:
      self.set_config('staging_server')
    else:
      self.set_config('public_server')

  def upload(self, results_file, test_type, chrome_revision,
             test_results_server=None, downgrade_error_to_warning=True,
             builder_name_suffix=''):
    """Upload results json to test-results.

    Args:
      results_file: Path to file containing result json. Supported format are:
        ttest format & full json results format (
        http://www.chromium.org/developers/the-json-test-results-format).
      test_type: Test type string, e.g. webkit_tests.
      test_results_server: Server where results should be uploaded.
      downgrade_error_to_warning: If True, treat a failure to upload as a
          warning.
      builder_name_suffix: Optional suffix to append to the builder name.

    Returns:
      The step result.
    """
    if builder_name_suffix:
      builder_name_suffix = '-%s' % builder_name_suffix
    try:
      upload_test_results_args = [
          '--input-json', results_file,
          '--master-name', self.m.properties['mastername'],
          '--builder-name', '%s%s' % (
              self.m.properties['buildername'], builder_name_suffix),
          '--build-number', self.m.properties['buildnumber'],
          '--test-type', test_type,
          '--chrome-revision', chrome_revision
      ]
      if self.m.buildbucket.build_id is not None:
        upload_test_results_args.extend(['--build-id', self.m.buildbucket.build_id])

      test_results_server = test_results_server or self.c.test_results_server
      if test_results_server:
        upload_test_results_args.extend([
            '--test-results-server',
            test_results_server
        ])

      return self.m.python(
          name='Upload to test-results [%s]' % test_type,
          script=self.resource('upload_test_results.py'),
          args=upload_test_results_args)
    except self.m.step.StepFailure as f:
      if downgrade_error_to_warning:
        f.result.presentation.status = self.m.step.WARNING
      return f.result

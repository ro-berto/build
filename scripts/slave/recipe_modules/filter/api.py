# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from slave import recipe_api

class FilterApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(FilterApi, self).__init__(**kwargs)
    self._result = False

  def __is_path_in_exclusion_list(self, path, exclusions):
    """Returns true if |path| matches any of the regular expressions in
    |exclusions|."""
    for regex in exclusions:
      match = regex.match(path)
      if match and match.end() == len(path):
        return regex.pattern
    return False

  @property
  def result(self):
    """Returns the result from most recent call to
    does_patch_require_compile."""
    return self._result


  def does_patch_require_compile(self, exclusions=None):
    """Return true if the current patch requires a build (and tests to run).
    Return value can be accessed by call to result().

    Args:
      exclusions: list of python regular expressions (as strings). If any of
      the files in the current patch match one of the values in |exclusions|
      True is returned."""

    exclusions = exclusions or self.m.properties.get('filter_exclusions', [])

    # Get the set of files in the current patch.
    step_result = self.m.git('diff', '--cached', '--name-only',
                             name='git diff to analyze patch',
                             stdout=self.m.raw_io.output(),
                             step_test_data=lambda:
                               self.m.raw_io.test_api.stream_output('foo.cc'))

    # Check the path of each file against the exclusion list. If found, no need
    # to check dependencies.
    exclusion_regexs = [re.compile(exclusion) for exclusion in exclusions]
    for path in step_result.stdout.split():
      first_match = self.__is_path_in_exclusion_list(path, exclusion_regexs)
      if first_match:
        step_result.presentation.logs.setdefault('excluded_files', []).append(
            '%s (regex = \'%s\')' % (path, first_match))
        self._result = 1
        return

    step_result = self.m.python('analyze',
                        self.m.path['checkout'].join('build', 'gyp_chromium'),
                        ['--analyzer',
                         self.m.raw_io.input(step_result.stdout)],
                        stdout = self.m.raw_io.output(),
                        step_test_data=lambda:
                          self.m.raw_io.test_api.stream_output('No dependency'))
    if step_result.stdout.find('Found dependency') != -1:
      self._result = True
    else:
      step_result.presentation.step_text = 'No compile necessary'

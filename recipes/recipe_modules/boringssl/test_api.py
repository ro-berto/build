# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from .api import TestResults


class BoringSslTestApi(recipe_test_api.RecipeTestApi):

  @recipe_test_api.placeholder_step_data
  def test_results(self, test_results_json, retcode=None, name=None):
    """Returns mock JSON output for a recipe step.

    The output will be promptly consumed by
    TestResultsOutputPlaceholder.result() to construct a TestResults instance.

    The name must be |test_results| to mirror the method |test_results| in
    test_utils/api.py

    Args:
      test_results_json - Mock JSON output from the test runner.
      retcode - The return code of the test runner.
    """
    return test_results_json, retcode, name

  def canned_test_output(self, passing):
    """Produces mock output for a recipe step that outputs a TestResults object.

    Args:
      passing - Determines if this test result is passing or not.

    Returns: A test_results placeholder.
    """
    if_failing = lambda fail_val: None if passing else fail_val
    t = TestResults({
        'version': 3,
        'path_separator': '/',
        'num_passes': 9001,
        'num_regressions': 0,
    })
    t.add_result('flake/totally-flakey.html', 'PASS',
                 if_failing('TIMEOUT PASS'))
    t.add_result('flake/timeout-then-crash.html', 'CRASH',
                 if_failing('TIMEOUT CRASH'))
    t.add_result('flake/slow.html', 'SLOW', if_failing('TIMEOUT SLOW'))
    t.add_result('tricky/totally-maybe-not-awesome.html', 'PASS',
                 if_failing('FAIL'))
    t.add_result('bad/totally-bad-probably.html', 'PASS', if_failing('FAIL'))
    t.add_result('good/totally-awesome.html', 'PASS')
    retcode = t.raw['num_regressions']
    return self.test_results(self.m.json.dumps(t.as_jsonish()), retcode)

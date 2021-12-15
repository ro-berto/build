# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import six

from recipe_engine import recipe_test_api

from PB.go.chromium.org.luci.resultdb.proto.v1 import (invocation as
                                                       rdb_invocation)
from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       rdb_test_result)
from PB.go.chromium.org.luci.resultdb.proto.v1 import common as rdb_common

from .util import GTestResults


class TestUtilsTestApi(recipe_test_api.RecipeTestApi):

  @recipe_test_api.placeholder_step_data
  def gtest_results(self, test_results_json, retcode=None, name=None):
    """Returns mock JSON output for a recipe step.

    The output will be promptly consumed by
    GTestResultsOutputPlaceholder.result() to construct a GTestResults instance.

    The name must be |gtest_results| to mirror the method |gtest_results| in
    test_utils/api.py

    Args:
      test_results_json - Mock JSON output from the test runner.
      retcode - The return code of the test runner.
    """
    return test_results_json, retcode, name

  def canned_gtest_output(self, passing, minimal=False, extra_json=None):
    """Produces mock output for a recipe step that outputs a GTestResults
    object.

    Args:
      passing - Determines if this test result is passing or not.
      minimal - If True, the canned output will omit one test to emulate the
                effect of running fewer than the total number of tests.
      extra_json - dict with additional keys to add to gtest JSON.
      name - Optional string name of the json output.

    Returns: A gtest_results placeholder
    """
    cur_iteration_data = {
      'Test.One': [
        {
          'elapsed_time_ms': 0,
          'output_snippet': ':)',
          'status': 'SUCCESS',
        },
      ],
      'Test.Two': [
        {
          'elapsed_time_ms': 0,
          'output_snippet': ':)' if passing else ':(',
          'status': 'SUCCESS' if passing else 'FAILURE',
        },
      ],
    }

    if not minimal:
      cur_iteration_data['Test.Three'] = [
        {
          'elapsed_time_ms': 0,
          'output_snippet': '',
          'status': 'SUCCESS',
        },
      ]

    canned_jsonish = {
      'per_iteration_data': [cur_iteration_data]
    }
    canned_jsonish.update(extra_json or {})

    retcode = None if passing else 1
    ret = self.gtest_results(self.m.json.dumps(canned_jsonish), retcode)
    return ret

  # TODO(tansell): https://crbug.com/704066 - Kill simplified JSON format.
  def generate_simplified_json_results(self, shard_indices,
                                       isolated_script_passing, valid):
    per_shard_results = []
    for i in shard_indices:
      jsonish_results = {}
      jsonish_results['valid'] = valid
      # Keep shard 0's results equivalent to the old code to minimize
      # expectation diffs.
      idx = 1 + (2 * i)
      tests_run = ['test%d.Test%d' % (idx, idx),
                   'test%d.Test%d' % (idx + 1, idx + 1)]
      if isolated_script_passing:
        jsonish_results['failures'] = []
        jsonish_results['successes'] = tests_run
      else:
        jsonish_results['failures'] = tests_run
        jsonish_results['successes'] = []
      jsonish_results['times'] = {t : 0.1 for t in tests_run}
      per_shard_results.append(jsonish_results)
    return per_shard_results

  def canned_isolated_script_output(self, passing, is_win=False, swarming=False,
                                    shards=1, shard_indices=None,
                                    swarming_internal_failure=False,
                                    isolated_script_passing=True,
                                    valid=None,
                                    missing_shards=None,
                                    output_chartjson=False,
                                    output_histograms=False,
                                    benchmark_enabled=True,
                                    corrupt=False,
                                    unknown=False,
                                    customized_test_results=None,
                                    add_shard_index=False, artifacts=None
                                    ):
    """Produces a test results' compatible json for isolated script tests.

    Args:
      artifacts: A dict of test basenames to dicts of test names to artifacts
          to add. Only used if use_json_test_format is True. For example, the
          following dict would add two screenshot artifacts to test1.Test1:
          {
            'test1': {
              'Test1': {
                'screenshot': ['some/path.png', 'another/path.png'],
              },
            },
          }
    """
    if not missing_shards:
      missing_shards = []
    per_shard_results = []
    per_shard_chartjson_results = []
    shard_indices = range(shards) if shard_indices is None else shard_indices
    for i in shard_indices:
      chartjsonish_results = {}
      idx = 1 + (2 * i)
      chartjsonish_results['dummy'] = 'dummy%d' % i
      chartjsonish_results['enabled'] = benchmark_enabled
      chartjsonish_results['charts'] = {
          'entry%d' % idx: 'chart%d' % idx,
          'entry%d' % (idx + 1): 'chart%d' % (idx + 1)
      }
      per_shard_chartjson_results.append(chartjsonish_results)
    if valid is None:
      valid = True
    per_shard_results = self.generate_simplified_json_results(
        shard_indices, isolated_script_passing, valid)

    if swarming:
      jsonish_shards = []
      files_dict = {}
      for index, i in enumerate(shard_indices):
        exit_code = '1' if not passing or swarming_internal_failure else '0'
        jsonish_shards.append({
          'failure': not passing,
          'internal_failure': swarming_internal_failure,
          'exit_code': exit_code,
        })
        swarming_path = str(i)
        swarming_path += '\\output.json' if is_win else '/output.json'

        chartjson_swarming_path = str(i)
        chartjson_swarming_path += \
          '\\perftest-output.json' \
            if is_win else '/perftest-output.json'

        # Determine what output we are writing and if it is empty or not
        output_missing = i in missing_shards and not output_chartjson

        if not output_missing:
          files_dict[swarming_path] = self.m.json.dumps(
              per_shard_results[index])

      jsonish_summary = {'shards': jsonish_shards}
      step_test_data = recipe_test_api.StepTestData()
      key = ('chromium_swarming', 'summary', None)
      placeholder = recipe_test_api.PlaceholderTestData(
          self.m.json.dumps(jsonish_summary))
      step_test_data.placeholder_data[key] = placeholder
      step_test_data += self.m.json.output(per_shard_results[0])

      files_dict['summary.json'] = self.m.json.dumps(jsonish_summary)
      files_dict = {k: v.encode('utf-8') for k, v in six.iteritems(files_dict)}
      step_test_data += self.m.raw_io.output_dir(files_dict)

      return step_test_data
    else:
      return self.m.json.output(per_shard_results[0])

  def rdb_results(self,
                  suite_name,
                  failing_tests=None,
                  skipped_tests=None,
                  flaky_tests=None):
    """Returns a JSON blob used to override data for 'query test results'.

    Args:
      suite_name: Name of the suite.
      failing_tests: List of test cases to create results for. Each test case
          will have a single rdb_test_result.FAIL result.
      skipped_tests: Same as failing_tests above, but with rdb_test_result.SKIP.
      flaky_tests: List of test cases which has two invocations,
          rdb_test_result.PASS and rdb_test_result.FAIL.
    """

    def _generate_invocation(test, status):
      test_result = rdb_test_result.TestResult(
          test_id=test,
          variant=rdb_common.Variant(**{
              'def': {
                  'test_suite': suite_name,
              },
          }),
          expected=status == rdb_test_result.PASS,
          variant_hash=suite_name + '_hash',
          status=status)
      return self.m.resultdb.Invocation(
          proto=rdb_invocation.Invocation(
              state=rdb_invocation.Invocation.FINALIZED,
              name=suite_name + '_results'),
          test_results=[test_result])

    failing_tests = failing_tests or []
    skipped_tests = skipped_tests or []
    flaky_tests = flaky_tests or []
    invocations = []
    for test in failing_tests:
      invocations.append(_generate_invocation(test, rdb_test_result.FAIL))
    for test in skipped_tests:
      invocations.append(_generate_invocation(test, rdb_test_result.SKIP))
    for test in flaky_tests:
      invocations.append(_generate_invocation(test, rdb_test_result.PASS))
      invocations.append(_generate_invocation(test, rdb_test_result.FAIL))

    invocations_by_inv_id = {}
    for i, inv in enumerate(invocations):
      invocations_by_inv_id['inv%d' % i] = inv
    return self.m.resultdb.serialize(invocations_by_inv_id)

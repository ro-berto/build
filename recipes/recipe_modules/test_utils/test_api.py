# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import recipe_test_api

from PB.go.chromium.org.luci.resultdb.proto.v1 import (invocation as
                                                       rdb_invocation)
from PB.go.chromium.org.luci.resultdb.proto.v1 import (test_result as
                                                       rdb_test_result)
from PB.go.chromium.org.luci.resultdb.proto.v1 import common as rdb_common

from .api import TestUtilsApi
from .util import GTestResults, TestResults

class TestUtilsTestApi(recipe_test_api.RecipeTestApi):
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

  # TODO(dpranke): Rewrite the BoringSSL recipe's tests to not use this routine,
  # and then delete this routine.
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
    return self.test_results(json.dumps(t.as_jsonish()), retcode)

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

  def canned_gtest_output(self,
                          passing,
                          minimal=False,
                          extra_json=None,
                          legacy_annotation=False):
    """Produces mock output for a recipe step that outputs a GTestResults
    object.

    Args:
      passing - Determines if this test result is passing or not.
      minimal - If True, the canned output will omit one test to emulate the
                effect of running fewer than the total number of tests.
      extra_json - dict with additional keys to add to gtest JSON.
      name - Optional string name of the json output.
      legacy_annotation - Set to true if the gtest is runned with output
                          annotated (i.e. emitting @@@annotation). This
                          is for supporting deprecated allow_subannotation
                          feature.

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
    ret = self.gtest_results(json.dumps(canned_jsonish), retcode)
    if legacy_annotation:
      ret += self.m.legacy_annotation.success_step if passing else (
          self.m.legacy_annotation.failure_step)
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

  def generate_json_test_results(self, shard_indices,
                                 isolated_script_passing, benchmark_enabled,
                                 customized_test_results,
                                 add_shard_index, artifacts):
    # pylint: disable=line-too-long
    """Generates fake test results in the JSON test results format.

    See https://chromium.googlesource.com/chromium/src/+/main/docs/testing/json_test_results_format.md
    for documentation on the format.

    Args:
      shard_indices: A list of shard indices to use.
      isolated_script_passing: A boolean denoting whether the generated results
          should mark the tests as passing or not.
      benchmark_enabled: A boolean denoting whether the tests should actually
          be shown as run or not.
      customized_test_results: A dict containing test results to use instead of
          generating new results.
      add_shard_index: A boolean denoting whether to add the shard index to
          failing test results or not.
      artifacts: A dict of test basenames to dicts of test names to artifacts
          to add. For example, the following dict would add two screenshot
          artifacts to test1.Test1:
          {
            'test1': {
              'Test1': {
                'screenshot': ['some/path.png', 'another/path.png'],
              },
            },
          }

    Returns:
      A list containing JSON test results for each shard.
    """
    per_shard_results = []
    for i in shard_indices:
      if customized_test_results:
        per_shard_results.append(customized_test_results)
        continue
      jsonish_results = {
        'interrupted': False,
        'path_delimiter': '.',
        'version': 3,
        'seconds_since_epoch': 14000000 + i,
        'num_failures_by_type': {
           'FAIL': 0,
           'PASS': 0
        }
      }
      idx = 1 + (3 * i)
      if isolated_script_passing and benchmark_enabled:
        tests_run = {
          'test_common': {
            'Test%d' % idx: {
              'expected': 'PASS',
              'actual': 'FAIL FAIL PASS',
            },
          },
          'test%d' % idx: {
            'Test%d' % idx: {
              'expected': 'PASS',
              'actual': 'PASS',
            },
            'Test%d' % (idx + 1): {
              'expected': 'PASS TIMEOUT',
              'actual': 'TIMEOUT',
             },
            'Test%d' % (idx + 2): {
              'expected': 'SKIP',
              'actual': 'SKIP',
             },
          }
        }
        jsonish_results['num_failures_by_type']['PASS'] = 2
        jsonish_results['num_failures_by_type']['SKIP'] = 1
      elif benchmark_enabled:
        test0_2_results = {
          'expected': 'PASS TIMEOUT',
          'actual': 'FAIL FAIL FAIL',
          'is_unexpected': True,
        }
        if add_shard_index:
          test0_2_results['shard'] = i
        tests_run = {
          'test%d' % idx: {
            'Test%d' % idx: {
              'expected': 'PASS',
              'actual': 'FAIL FAIL TIMEOUT',
            },
            'Test%d' % (idx + 1): {
              'expected': 'PASS TIMEOUT',
              'actual': 'FAIL FAIL FAIL',
              'is_unexpected': True,
            },
            'Test%d-2' % (idx + 1): test0_2_results,
          }
        }

        jsonish_results['num_failures_by_type']['FAIL'] = 2
      else:
        tests_run = {}

      for test_basename, subtests in tests_run.iteritems():
        for test_name, test_dict in subtests.iteritems():
          test_artifacts = artifacts.get(test_basename, {}).get(test_name, {})
          if test_artifacts:
            test_dict['artifacts'] = test_artifacts

      jsonish_results['tests'] = tests_run
      per_shard_results.append(jsonish_results)
    return per_shard_results

  def canned_isolated_script_output(self, passing, is_win=False, swarming=False,
                                    shards=1, shard_indices=None,
                                    swarming_internal_failure=False,
                                    isolated_script_passing=True,
                                    isolated_script_retcode=None,
                                    valid=None,
                                    missing_shards=None,
                                    empty_shards=None,
                                    use_json_test_format=False,
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
    if not empty_shards:
      empty_shards = []
    per_shard_results = []
    per_shard_chartjson_results = []
    shard_indices = range(shards) if shard_indices is None else shard_indices
    for i in shard_indices:
      if output_histograms:
        histogramish_results = []
        idx = 1 + (2 * i)
        histogramish_results.append(
            {'guid': '%s' % idx, 'name': 'foo%d' % idx, 'unit': 'count'})
        per_shard_chartjson_results.append(histogramish_results)
      else:
        chartjsonish_results = {}
        idx = 1 + (2 * i)
        chartjsonish_results['dummy'] =  'dummy%d' % i
        chartjsonish_results['enabled'] = benchmark_enabled
        chartjsonish_results['charts'] = {'entry%d' % idx: 'chart%d' % idx,
          'entry%d' % (idx + 1): 'chart%d' % (idx + 1)}
        per_shard_chartjson_results.append(chartjsonish_results)
    if use_json_test_format:
      assert valid is None, "valid flag not used in full JSON format."
      artifacts = artifacts or {}
      per_shard_results = self.generate_json_test_results(
          shard_indices, isolated_script_passing, benchmark_enabled,
          customized_test_results, add_shard_index, artifacts)
    else:
      if valid is None:
        valid = True
      per_shard_results = self.generate_simplified_json_results(
          shard_indices, isolated_script_passing, valid)

    if unknown:
      per_shard_results[0]['tests']['test1']['Test1']['actual'] = 'UNKNOWN'
    if corrupt:
      per_shard_results[0]['tests'] = 'corrupted'

    if swarming:
      jsonish_shards = []
      files_dict = {}
      for index, i in enumerate(shard_indices):
        if isolated_script_retcode is None:
          exit_code = '1' if not passing or swarming_internal_failure else '0'
        else:
          exit_code = str(isolated_script_retcode)
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
        chartjson_output_missing = i in missing_shards and output_chartjson
        output_empty = i in empty_shards and not output_chartjson
        chartjson_output_empty = i in empty_shards and output_chartjson

        if not output_missing:
          files_dict[swarming_path] = \
            '' if output_empty else json.dumps(per_shard_results[index])
        if not chartjson_output_missing and output_chartjson:
          files_dict[chartjson_swarming_path] = \
            '' if chartjson_output_empty \
              else json.dumps(per_shard_chartjson_results[index])

      jsonish_summary = {'shards': jsonish_shards}
      step_test_data = recipe_test_api.StepTestData()
      key = ('chromium_swarming', 'summary', None)
      placeholder = recipe_test_api.PlaceholderTestData(
          json.dumps(jsonish_summary))
      step_test_data.placeholder_data[key] = placeholder
      step_test_data += self.m.json.output(per_shard_results[0])

      files_dict['summary.json'] = json.dumps(jsonish_summary)
      step_test_data += self.m.raw_io.output_dir(files_dict)

      return step_test_data
    else:
      return self.m.json.output(per_shard_results[0])

  def simulated_gtest_output(self, failed_test_names=(), passed_test_names=(),
                             flaky_test_names=()):
    cur_iteration_data = {}
    for test_name in failed_test_names:
      cur_iteration_data[test_name] = [{
          'elapsed_time_ms': 0,
          'output_snippet': ':(',
          'status': 'FAILURE',
      }]
    for test_name in passed_test_names:
      cur_iteration_data[test_name] = [{
          'elapsed_time_ms': 0,
          'output_snippet': ':)',
          'status': 'SUCCESS',
      }]

    for test_name in flaky_test_names:
      cur_iteration_data[test_name] = [
          {
              'elapsed_time_ms': 0,
              'output_snippet': ':)',
              'status': 'SUCCESS',
          },
          {
              'elapsed_time_ms': 0,
              'output_snippet': ':(',
              'status': 'FAILURE',
          }
      ]

    canned_jsonish = {
        'per_iteration_data': [cur_iteration_data]
    }

    return self.gtest_results(json.dumps(canned_jsonish),
                              retcode=1 if failed_test_names else 0)

  def simulated_isolated_script_output(
      self, failed_test_names=(), passed_test_names=(),
      flaky_test_names=(), path_delimiter='.'):

    flat_tests = {}
    for test_name in failed_test_names:
      flat_tests[test_name] = {
        'expected': 'PASS',
        'actual': 'FAIL',
        'is_unexpected': True,
      }
    for test_name in passed_test_names:
      flat_tests[test_name] = {
        'expected': 'PASS',
        'actual': 'PASS'
      }

    for test_name in flaky_test_names:
      flat_tests[test_name] = {
        'expected': 'PASS',
        'actual': 'FAIL PASS'
      }

    tests = {}
    def convert_flat_test_to_trie(test_name_parts, test_result, trie_test):
      if len(test_name_parts) == 1:
        trie_test[test_name_parts[0]] = test_result
      else:
        trie_test[test_name_parts[0]] = trie_test.get(test_name_parts[0]) or {}
        convert_flat_test_to_trie(
          test_name_parts[1:], test_result, trie_test[test_name_parts[0]])

    for test_name, test_result in flat_tests.iteritems():
      parts = test_name.split(path_delimiter)
      convert_flat_test_to_trie(
        parts, test_result, tests)

    canned_jsonish = {
        'tests': tests,
        'interrupted': False,
        'path_delimiter': path_delimiter,
        'version': 3,
    }

    jsonish_summary = {
        'shards': [canned_jsonish],
        'failure': bool(failed_test_names),
        'internal_failure': False,
        'exit_code': 1 if failed_test_names else 0,
    }
    files_dict = {'summary.json': json.dumps(jsonish_summary)}
    retcode = 1 if failed_test_names else 0
    return (self.m.raw_io.output_dir(files_dict) +
            self.m.json.output(canned_jsonish, retcode))

  def rdb_results(self, failing_suites=None):
    """Returns a JSON blob used to override data for 'query test results'.

    Args:
      failing_suites: List of names of the failing suites to create results
          for. Each suite will have a single test with a rdb_test_result.FAIL
          result.
    """

    def _generate_invocation(suite, is_failure=False):
      status = rdb_test_result.FAIL if is_failure else rdb_test_result.PASS
      test_result = rdb_test_result.TestResult(
          test_id=suite + '_test_case1',
          variant=rdb_common.Variant(**{
              'def': {
                  'test_suite': suite,
              },
          }),
          expected=not is_failure,
          status=status)
      return self.m.resultdb.Invocation(
          proto=rdb_invocation.Invocation(
              state=rdb_invocation.Invocation.FINALIZED,
              name=suite + '_results'),
          test_results=[test_result])

    failing_suites = failing_suites or []
    invocations = []
    for suite in failing_suites:
      invocations.append(_generate_invocation(suite, is_failure=True))

    invocations_by_inv_id = {}
    for i, inv in enumerate(invocations):
      invocations_by_inv_id['inv%d' % i] = inv
    return self.m.resultdb.serialize(invocations_by_inv_id)

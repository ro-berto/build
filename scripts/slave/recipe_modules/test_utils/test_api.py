import json

from recipe_engine import recipe_test_api

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

  def canned_test_output(self, passing, minimal=False, passes=9001,
                         num_additional_failures=0,
                         path_separator=None,
                         retcode=None,
                         unexpected_flakes=False):
    """Produces mock output for a recipe step that outputs a TestResults object.

    Args:
      passing - Determines if this test result is passing or not.
      passes - The number of (theoretically) passing tests.
      minimal - If True, the canned output will omit one test to emulate the
                effect of running fewer than the total number of tests.
      num_additional_failures - the number of failed tests to simulate in
                addition to the three generated if passing is False

    Returns: A test_results placeholder
    """
    if_failing = lambda fail_val: None if passing else fail_val
    t = TestResults({'version': 3})
    sep = path_separator or '/'
    t.raw['path_separator'] = sep
    t.raw['num_passes'] = passes
    t.raw['num_regressions'] = 0
    t.add_result('flake%stotally-flakey.html' % sep, 'PASS',
                 if_failing('TIMEOUT PASS'))
    t.add_result('flake%stimeout-then-crash.html' % sep, 'CRASH',
                 if_failing('TIMEOUT CRASH'))
    t.add_result('flake%sslow.html' % sep, 'SLOW',
                 if_failing('TIMEOUT SLOW'))
    t.add_result('tricky%stotally-maybe-not-awesome.html' % sep, 'PASS',
                 if_failing('FAIL'))
    t.add_result('bad%stotally-bad-probably.html' % sep, 'PASS',
                 if_failing('FAIL'))
    if not minimal:
      t.add_result('good%stotally-awesome.html' % sep, 'PASS')
    for i in xrange(num_additional_failures):
        t.add_result('bad%sfailing%d.html' % (sep, i), 'PASS', 'FAIL')
    if unexpected_flakes:
      t.add_result('flake%sflakey.html' % sep, 'PASS', 'FAIL PASS')

    if not passing and retcode is None:
      retcode = min(
          t.raw['num_regressions'], TestUtilsApi.MAX_FAILURES_EXIT_STATUS)

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
    return self.gtest_results(json.dumps(canned_jsonish), retcode)

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
                                 customized_test_results):
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
            'Test%d-2' % (idx + 1): {
              'expected': 'PASS TIMEOUT',
               'actual': 'FAIL FAIL FAIL',
               'is_unexpected': True,
             },
          }
        }

        jsonish_results['num_failures_by_type']['FAIL'] = 2
      else:
        tests_run = {}
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
                                    customized_test_results=None
                                    ):
    """Produces a test results' compatible json for isolated script tests. """
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
      per_shard_results = self.generate_json_test_results(
          shard_indices, isolated_script_passing, benchmark_enabled,
          customized_test_results)
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
      for i in shard_indices:
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
            '' if output_empty else json.dumps(per_shard_results[i])
        if not chartjson_output_missing and output_chartjson:
          files_dict[chartjson_swarming_path] = \
            '' if chartjson_output_empty \
              else json.dumps(per_shard_chartjson_results[i])

      jsonish_summary = {'shards': jsonish_shards}
      files_dict['summary.json'] = json.dumps(jsonish_summary)
      return (self.m.raw_io.output_dir(files_dict)
              + self.m.json.output(per_shard_results[0]))
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

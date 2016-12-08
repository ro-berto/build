import json

from recipe_engine import recipe_test_api

from .util import GTestResults, TestResults

class TestUtilsTestApi(recipe_test_api.RecipeTestApi):
  @recipe_test_api.placeholder_step_data
  def test_results(self, test_results, retcode=None):
    return self.m.json.output(test_results.as_jsonish(), retcode)

  def canned_test_output(self, passing, minimal=False, passes=9001,
                         num_additional_failures=0,
                         path_separator=None,
                         retcode=None,
                         unexpected_flakes=False):
    """Produces a 'json test results' compatible object with some canned tests.
    Args:
      passing - Determines if this test result is passing or not.
      passes - The number of (theoretically) passing tests.
      minimal - If True, the canned output will omit one test to emulate the
                effect of running fewer than the total number of tests.
      num_additional_failures - the number of failed tests to simulate in
                addition to the three generated if passing is False
    """
    if_failing = lambda fail_val: None if passing else fail_val
    t = TestResults()
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
    ret = self.test_results(t)
    if retcode is not None:
        ret.retcode = retcode
    else:
        ret.retcode = min(t.raw['num_regressions'], t.MAX_FAILURES_EXIT_STATUS)
    return ret

  def raw_test_output(self, jsonish, retcode):
    t = TestResults(jsonish)
    ret = self.test_results(t)
    ret.retcode = retcode
    return ret

  @recipe_test_api.placeholder_step_data
  def gtest_results(self, test_results, retcode=None):
    return self.m.json.output(test_results.as_jsonish(), retcode)

  def canned_gtest_output(self, passing, minimal=False, passes=9001,
                          extra_json=None):
    """Produces a 'json test results' compatible object with some canned tests.
    Args:
      passing - Determines if this test result is passing or not.
      passes - The number of (theoretically) passing tests.
      minimal - If True, the canned output will omit one test to emulate the
                effect of running fewer than the total number of tests.
      extra_json - dict with additional keys to add to gtest JSON.
    """
    cur_iteration_data = {
      'Test.One': [
        {
          'elapsed_time_ms': 0,
          'output_snippet': '',
          'status': 'SUCCESS',
        },
      ],
      'Test.Two': [
        {
          'elapsed_time_ms': 0,
          'output_snippet': '',
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
    return self.raw_gtest_output(canned_jsonish, retcode)

  def raw_gtest_output(self, jsonish, retcode):
    t = GTestResults(jsonish)
    ret = self.gtest_results(t)
    ret.retcode = retcode
    return ret

  def generate_simplified_json_results(self, shards, isolated_script_passing,
                                       valid):
    per_shard_results = []
    for i in xrange(shards):
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

  def generate_json_test_results(self, shards, isolated_script_passing,
                                 valid):
    per_shard_results = []
    for i in xrange(shards):
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
      if not valid:
        jsonish_results['invalid'] = '1'
      idx = 1 + (2 * i)
      if isolated_script_passing:
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
          }
        }
        jsonish_results['num_failures_by_type']['PASS'] = 2
      else:
        tests_run = {
          'test%d' % idx: {
            'Test%d' % idx: {
              'expected': 'PASS',
              'actual': 'FAIL FAIL TIMEOUT',
            },
            'Test%d' % (idx + 1): {
              'expected': 'PASS TIMEOUT',
               'actual': 'FAIL FAIL FAIL',
             },
          }
        }

        jsonish_results['num_failures_by_type']['FAIL'] = 2
      jsonish_results['tests'] = tests_run
      per_shard_results.append(jsonish_results)
    return per_shard_results

  def canned_isolated_script_output(self, passing, is_win, swarming=False,
                                    shards=1, swarming_internal_failure=False,
                                    isolated_script_passing=True, valid=True,
                                    missing_shards=[],
                                    empty_shards=[],
                                    use_json_test_format=False,
                                    output_chartjson=False,
                                    benchmark_enabled=True):
    """Produces a test results' compatible json for isolated script tests. """
    per_shard_results = []
    per_shard_chartjson_results = []
    for i in xrange(shards):
      chartjsonish_results = {}
      idx = 1 + (2 * i)
      chartjsonish_results['dummy'] =  'dummy%d' % i
      chartjsonish_results['enabled'] = benchmark_enabled
      chartjsonish_results['charts'] = {'entry%d' % idx: 'chart%d' % idx,
        'entry%d' % (idx + 1): 'chart%d' % (idx + 1)}
      per_shard_chartjson_results.append(chartjsonish_results)
    if use_json_test_format:
      per_shard_results = self.generate_json_test_results(
          shards, isolated_script_passing, valid)
    else:
      per_shard_results = self.generate_simplified_json_results(
          shards, isolated_script_passing, valid)
    if swarming:
      jsonish_shards = []
      files_dict = {}
      for i in xrange(shards):
        jsonish_shards.append({
          'failure': not passing,
          'internal_failure': swarming_internal_failure,
          'exit_code': '1' if not passing or swarming_internal_failure else '0'
        })
        swarming_path = str(i)
        swarming_path += '\\output.json' if is_win else '/output.json'

        chartjson_swarming_path = str(i)
        chartjson_swarming_path += \
          '\\chartjson-output.json' \
            if is_win else '/chartjson-output.json'

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
      return self.m.raw_io.output_dir(files_dict)
    else:
      return self.m.json.output(per_shard_results[0])

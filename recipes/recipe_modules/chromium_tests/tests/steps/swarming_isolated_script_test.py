# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/bot_update',
    'isolate',
    'profiles',
    'recipe_engine/commit_position',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'test_results',
    'test_utils',
]

from recipe_engine import post_process
import json

from RECIPE_MODULES.build.chromium_tests import steps


def RunSteps(api):
  api.chromium.set_build_properties({
      'got_webrtc_revision': 'webrtc_sha',
      'got_v8_revision': 'v8_sha',
  })
  api.chromium.set_config('chromium')
  # Fake path, as the real one depends on having done a chromium checkout.
  api.profiles._merge_scripts_dir = api.path['start_dir']

  _, bot_config = api.chromium_tests.lookup_builder()
  api.chromium_tests.configure_build(bot_config)
  api.chromium_tests.prepare_checkout(bot_config)

  test_repeat_count = api.properties.get('repeat_count')
  if api.properties.get('swarm_hashes'):
    swarm_hashes = api.properties['swarm_hashes']
    assert len(swarm_hashes) == 1
    test_name = list(swarm_hashes.keys())[0]
  else:
    # Needed for a test
    test_name = 'base_unittests'
  isolate_coverage_data = api.properties.get('isolate_coverage_data', False)
  test_spec = steps.SwarmingIsolatedScriptTestSpec.create(
      name=test_name,
      ignore_task_failure=api.properties.get('ignore_task_failure'),
      override_compile_targets=api.properties.get('override_compile_targets'),
      io_timeout=120,
      hard_timeout=360,
      expiration=7200,
      shards=int(api.properties.get('shards', '1')) or 1,
      dimensions=api.properties.get('dimensions', {
          'gpu': '8086',
      }),
      isolate_coverage_data=isolate_coverage_data,
      resultdb=steps.ResultDB.create(enable=True))
  test = test_spec.get_test()
  api.chromium_swarming.set_default_dimension('pool', 'foo')
  assert test.runs_on_swarming and not test.is_gtest
  assert test.shards > 0

  if test_repeat_count:
    test.test_options = steps.TestOptions(
        test_filter=api.properties.get('test_filter'),
        repeat_count=test_repeat_count,
        retry_limit=0,
        run_disabled=bool(test_repeat_count))

  try:
    test.pre_run(api, 'with patch')
    test.run(api, 'with patch')

  finally:
    if api.properties.get('run_without_patch'):
      test._only_retry_failed_tests = True

      test.pre_run(api, 'without patch')
      test.run(api, 'without patch')

    result = api.step('details', [])
    result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(),
        'uses_local_devices: %r' % test.uses_local_devices,
        'uses_isolate: %r' % test.uses_isolate,
    ]
    if test_name == 'blink_web_tests':
      result.presentation.logs['details'].append(
          'pass_fail_counts: %r' % test.pass_fail_counts(suffix='with patch'))
      result.presentation.logs['details'].append(
          'has_valid_results: %r' % test.has_valid_results('with patch'))


def GenTests(api):

  def verify_log_fields(check, step_odict, expected_fields):
    """Verifies fields in details log are with expected values."""
    step = step_odict['details']
    for field in expected_fields.iteritems():
      expected_log = '%s: %r' % field
      check(expected_log in step.logs['details'])

  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },),
  )

  yield api.test(
      'basic_cas',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(swarm_hashes={
          'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff/111',
      }),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_shards',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'blink_web_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },),
      api.override_step_data(
          'blink_web_tests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.m.json.output({
                  'missing_shards': [0],
              }, 0),
              shards=1)),
      api.post_process(verify_log_fields, {'has_valid_results': False}),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'isolate_coverage_data',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          isolate_coverage_data=True,
      ),
      api.post_check(
          api.swarming.check_triggered_request,
          '[trigger] base_unittests on Intel GPU on Linux (with patch)',
          lambda check, req: check('LLVM_PROFILE_FILE' in req[0].env_vars),
      ),
      api.post_process(post_process.StepCommandContains,
                       'base_unittests on Intel GPU on Linux (with patch)',
                       ['[START_DIR]/merge_results.py']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'fail',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },),
      api.step_data(
          '[trigger] base_unittests on Intel GPU on Linux (with patch)',
          retcode=1),
      api.post_process(post_process.StatusAnyFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'fail_many_failures',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          shards=20,
          run_without_patch=True,
      ),
      api.step_data(
          '[trigger] base_unittests on Intel GPU on Linux (with patch)',
          retcode=1,
      ),
      api.post_process(post_process.StatusAnyFailure),
      api.post_process(
          post_process.Filter(
              '[trigger] base_unittests on Intel GPU on Linux (without patch)')
      ),
  )

  yield api.test(
      'fail_to_trigger',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  isolated_script_output = api.test_utils.canned_isolated_script_output(
      passing=False, swarming=True, benchmark_enabled=True,
      isolated_script_passing=False,
      shards=4, use_json_test_format=True)
  yield api.test(
      'without_patch_filter',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          run_without_patch='a'),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              isolated_script_output, failure=True, retcode=1)),
      api.post_process(
          post_process.Filter(
              '[trigger] base_unittests on Intel GPU on Linux (without patch)')
      ),
  )

  isolated_script_output = api.test_utils.canned_isolated_script_output(
      passing=False, swarming=True, benchmark_enabled=True,
      isolated_script_passing=False,
      shards=1, use_json_test_format=True,
      customized_test_results={
        'interrupted': False,
        'path_delimiter': '.',
        'version': 3,
        'seconds_since_epoch': 14000000,
        'num_failures_by_type': {
          'FAIL': 2,
          'PASS': 0
        },
        'tests': {
          'test1': {
            'Test1': {
              'expected': '',
              'actual': 'FAIL'
            },
            'Test2': {
              'expected': 'FAIL',
              'actual': 'TEXT'
            },
            'Test3': {
              'expected': 'FAIL',
              'actual': 'PASS'
            },
            'Test4': {
              'expected': '',
              'actual': 'PASS'
            }
          }
        },
      })

  yield api.test(
      'expected_failures',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'blink_web_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          test_filter=['test1', 'test2'],
          repeat_count=20),
      api.override_step_data(
          'blink_web_tests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              isolated_script_output, failure=True)),
      api.post_process(
          verify_log_fields, {
              'pass_fail_counts': {
                  'test1.Test1': {
                      'pass_count': 0,
                      'fail_count': 1
                  },
                  'test1.Test2': {
                      'pass_count': 1,
                      'fail_count': 0
                  },
                  'test1.Test3': {
                      'pass_count': 1,
                      'fail_count': 0
                  },
                  'test1.Test4': {
                      'pass_count': 1,
                      'fail_count': 0
                  }
              }
          }),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'customized_test_options',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'blink_web_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          test_filter=['test1', 'test2'],
          repeat_count=20),
      api.post_process(
          verify_log_fields, {
              'pass_fail_counts': {
                  'test_common.Test1': {
                      'pass_count': 1,
                      'fail_count': 2
                  },
                  'test1.Test1': {
                      'pass_count': 1,
                      'fail_count': 0
                  },
                  'test1.Test2': {
                      'pass_count': 1,
                      'fail_count': 0
                  },
                  'test1.Test3': {
                      'pass_count': 0,
                      'fail_count': 0
                  }
              }
          }),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'override_compile_targets',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          override_compile_targets=['base_unittests_run']),
  )

  yield api.test(
      'chartjson',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          perf_builder_name_alias='test-perf-id',
          results_url='https://example/url'),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  output_chartjson=True,
                  use_json_test_format=True),
              shards=2)),
  )

  # Uses simplified json
  # https://crbug.com/704066
  yield api.test(
      'chartjson_simplified_ignore_task_failure',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          perf_builder_name_alias='test-perf-id',
          results_url='https://example/url',
          ignore_task_failure=True),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=False,
                  valid=True,
                  output_chartjson=True),
              shards=2)),
  )

  yield api.test(
      'chartjson_ignore_task_failure',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          perf_builder_name_alias='test-perf-id',
          results_url='https://example/url',
          ignore_task_failure=True),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=False,
                  output_chartjson=True,
                  use_json_test_format=True),
              shards=2)),
  )

  # Uses simplied json
  # https://crbug.com/704066
  yield api.test(
      'chartjson_invalid',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          perf_builder_name_alias='test-perf-id',
          results_url='https://example/url'),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  valid=False,
                  output_chartjson=True),
              shards=2),
          retcode=0),
  )

  yield api.test(
      'chartjson_max_failures',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          perf_builder_name_alias='test-perf-id',
          results_url='https://example/url'),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  output_chartjson=True,
                  use_json_test_format=True),
              shards=2),
          retcode=102),
  )

  yield api.test(
      'chartjson_no_results',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          perf_builder_name_alias='test-perf-id',
          results_url='https://example/url'),
  )

  yield api.test(
      'chartjson_no_results_failure',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          perf_builder_name_alias='test-perf-id',
          results_url='https://example/url'),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.m.json.output(None, 255), failure=True)),
  )

  yield api.test(
      'chartjson_not_uploading',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp='refs/heads/master@{#123456}'),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  output_chartjson=True,
                  use_json_test_format=True),
              shards=2)),
  )

  yield api.test(
      'chartjson_disabled',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          perf_builder_name_alias='test-perf-id',
          results_url='https://example/url'),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  output_chartjson=True,
                  benchmark_enabled=False,
                  use_json_test_format=True),
              shards=2)),
  )

  # Uses simplied json
  # https://crbug.com/704066

  yield api.test(
      'chartjson_simplified_disabled',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          perf_builder_name_alias='test-perf-id',
          results_url='https://example/url'),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  valid=True,
                  output_chartjson=True,
                  benchmark_enabled=False),
              shards=2)),
  )

  placeholder_test_output = (api.test_utils.canned_isolated_script_output(
      passing=True, swarming=True,
      shards=2, isolated_script_passing=True,
      output_chartjson=True, benchmark_enabled=True,
      use_json_test_format=True, output_histograms=True) +
      api.chromium_swarming.merge_script_log_file('Merge succesfully'))
  yield api.test(
      'histograms',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          got_webrtc_revision='ffffffffffffffffffffffffffffffffffffffff',
          got_v8_revision='ffffffffffffffffffffffffffffffffffffffff',
          perf_builder_name_alias='test-perf-id',
          perf_dashboard_machine_group='ChromePerf',
          results_url='https://example/url'),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              placeholder_test_output, shards=2)),
  )

  yield api.test(
      'histograms_LUCI_missing_perf_dashboard_machine_group_property',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          got_webrtc_revision='ffffffffffffffffffffffffffffffffffffffff',
          got_v8_revision='ffffffffffffffffffffffffffffffffffffffff',
          perf_builder_name_alias='test-perf-id',
          results_url='https://example/url'),
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  output_chartjson=True,
                  benchmark_enabled=True,
                  use_json_test_format=True,
                  output_histograms=True),
              shards=2)),
  )

  yield api.test(
      'dimensions_windows',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          dimensions={
              'gpu': '8086',
              'os': 'Windows',
          }),
  )

  yield api.test(
      'dimensions_mac',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          dimensions={
              'gpu': '8086',
              'os': 'Mac',
          }),
  )

  yield api.test(
      'dimensions_mac_hidpi',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          dimensions={
              'gpu': '8086',
              'os': 'Mac',
              'hidpi': '1',
          }),
  )

  yield api.test(
      'dimensions_mac_intel_stable',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          dimensions={
              'gpu': '8086',
              'os': 'mac-intel-stable',
          }),
      api.override_step_data(
          'base_unittests on Intel GPU on Mac (with patch) '
          'on mac-intel-stable',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  swarming=True,
                  isolated_script_passing=False,
                  shards=1,
                  use_json_test_format=True,
                  customized_test_results={
                      'interrupted': False,
                      'path_delimiter': '.',
                      'version': 3,
                      'seconds_since_epoch': 14000000,
                      'num_failures_by_type': {
                          'FAIL': 2,
                          'PASS': 0
                      },
                      'tests': {
                          'test1': {
                              'Test1': {
                                  'expected': '',
                                  'actual': 'FAIL'
                              },
                          }
                      },
                  }))),
      api.post_process(
          post_process.StepSuccess,
          'Upload to test-results [base_unittests on Intel GPU on Mac '
          '(with patch) on mac-intel-stable]'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'dimensions_android',
      api.chromium.ci_build(
          builder_group='chromium.android',
          builder='Lollipop Phone Tester',
      ),
      api.properties(
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          dimensions={
              'device_type': 'hammerhead',
              'device_os': 'LOL123',
              'os': 'Android',
          }),
  )

  yield api.test(
      'invalid_test_results',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'blink_web_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          test_filter=['test1', 'test2'],
          repeat_count=20),
      api.override_step_data(
          'blink_web_tests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.m.json.output(None, 255), shards=2)),
      api.post_process(verify_log_fields, {'pass_fail_counts': {}}),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'unreliable_results',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.properties(
          swarm_hashes={
              'blink_web_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          test_filter=['test1', 'test2'],
          repeat_count=20),
      api.override_step_data(
          'blink_web_tests on Intel GPU on Linux (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.m.json.output(
                  {'global_tags': ['UNRELIABLE_RESULTS']}, 0),
              shards=2)),
      api.post_process(post_process.StepException,
                       'blink_web_tests on Intel GPU on Linux (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

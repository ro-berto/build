# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'build',
    'chromium',
    'chromium_checkout',
    'chromium_tests',
    'commit_position',
    'depot_tools/bot_update',
    'isolate',
    'perf_dashboard',
    'puppet_service_account',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'swarming',
    'test_results',
    'test_utils',
]

from recipe_engine import post_process
import json


def RunSteps(api):
  api.chromium.set_build_properties({
      'got_webrtc_revision': 'webrtc_sha',
      'got_v8_revision': 'v8_sha',
  })
  api.chromium.set_config('chromium')

  bot_config_object = api.chromium_tests.create_bot_config_object([
      api.chromium_tests.create_bot_id(
          api.properties['mastername'], api.properties['buildername'])])
  api.chromium_tests.configure_build(bot_config_object)
  api.chromium_tests.prepare_checkout(bot_config_object)

  test_repeat_count = api.properties.get('repeat_count')
  test_name = 'webkit_layout_tests' if test_repeat_count else 'base_unittests'
  isolate_coverage_data = api.properties.get('isolate_coverage_data', False)
  test = api.chromium_tests.steps.SwarmingIsolatedScriptTest(
      test_name,
      perf_id=api.properties.get('perf_id'),
      perf_dashboard_id='test-perf-dashboard-id',
      results_url=api.properties.get('results_url'),
      ignore_task_failure=api.properties.get('ignore_task_failure'),
      override_compile_targets=api.properties.get('override_compile_targets'),
      io_timeout=120,
      hard_timeout=360,
      expiration=7200,
      priority='lower',
      shards=int(api.properties.get('shards', '1')) or 1,
      dimensions=api.properties.get('dimensions', {'gpu': '8086'}),
      isolate_coverage_data=isolate_coverage_data,
  )
  assert test.runs_on_swarming and not test.is_gtest

  if test_repeat_count:
      test.test_options = api.chromium_tests.steps.TestOptions(
          test_filter=api.properties.get('test_filter'),
          repeat_count=test_repeat_count,
          retry_limit=0,
          run_disabled=bool(test_repeat_count)
      )

  try:
    # Emulate the behavior test_utils uses to run tests. Needed to achieve
    # coverage of some code.
    try:
      test.pre_run(api, 'with patch')
    except api.step.InfraFailure:
      raise
    except api.step.StepFailure:
      # Swarming isolated script tests never abort on failure
      pass
    test.run(api, 'with patch')

  finally:
    if api.properties.get('run_without_patch'):
      test._only_retry_failed_tests = True

      test.pre_run(api, 'without patch')
      test.run(api, 'without patch')

    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
      'compile_targets: %r' % test.compile_targets(api),
      'uses_local_devices: %r' % test.uses_local_devices,
      'uses_isolate: %r' % test.uses_isolate,
    ]
    if test_repeat_count:
      api.step.active_result.presentation.logs['details'].append(
        'pass_fail_counts: %r' % test.pass_fail_counts(
            api, suffix='with patch')
      )


def GenTests(api):

  def verify_log_fields(check, step_odict, expected_fields):
    """Verifies fields in details log are with expected values."""
    step = step_odict['details']
    followup_annotations = step['~followup_annotations']
    for key, value in expected_fields.iteritems():
      expected_log = '@@@STEP_LOG_LINE@details@%s: %r@@@' % (key, value)
      check(expected_log in followup_annotations)
    return step_odict

  def verify_isolate_flag(check, step_odict):
    step = step_odict[
        '[trigger] base_unittests on Intel GPU on Linux (with patch)']
    check('LLVM_PROFILE_FILE' in step['cmd'])
    step = step_odict[
        'base_unittests on Intel GPU on Linux (with patch)']
    # Make sure swarming collect know how to merge coverage profile data.
    check('RECIPE_MODULE[build::clang_coverage]/resources/merge_profiles.py'
          in step['cmd'])

  yield (
      api.test('basic') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456)
  )

  yield (
      api.test('isolate_coverage_data') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          isolate_coverage_data=True,
      ) +
      api.post_process(verify_isolate_flag) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('fail') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456) +
      api.step_data(
          '[trigger] base_unittests on Intel GPU on Linux (with patch)',
          retcode=1) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('fail_many_failures') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          shards=20,
          run_without_patch=True,
          got_revision_cp=123456) +
      api.step_data(
          '[trigger] base_unittests on Intel GPU on Linux (with patch)',
          retcode=1, ) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.Filter(
          '[trigger] base_unittests on Intel GPU on Linux (without patch)'))
  )

  yield (
      api.test('fail_to_trigger') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('basic_luci') +
      api.properties.generic(
          buildbucket=json.dumps({
            'build':{
              'project':'chromium',
              'bucket':'try',
              'tags':['builder:Linux Tests'],
            }}),
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456)
  )

  yield (
      api.test('without_patch_filter') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          run_without_patch='a') +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(failure=True)
          + api.test_utils.canned_isolated_script_output(
              passing=False, swarming=True, benchmark_enabled=True,
              isolated_script_passing=False,
              shards=4, use_json_test_format=True),
          retcode=1) +
      api.post_process(post_process.Filter(
          '[trigger] base_unittests on Intel GPU on Linux (without patch)'))
  )

  yield (
      api.test('expected_failures') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'webkit_layout_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          test_filter=['test1', 'test2'],
          repeat_count=20) +
      api.override_step_data(
          'webkit_layout_tests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(failure=True)
          + api.test_utils.canned_isolated_script_output(
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
              }),
          retcode=0) +
      api.post_process(
          verify_log_fields,
          {'pass_fail_counts': {
              'test1.Test1': {
                  'pass_count': 0,
                  'fail_count': 1},
              'test1.Test2': {
                  'pass_count': 1,
                  'fail_count': 0},
              'test1.Test3': {
                  'pass_count': 1,
                  'fail_count': 0},
              'test1.Test4': {
                  'pass_count': 1,
                  'fail_count': 0}}}) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('customized_test_options') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'webkit_layout_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          test_filter=['test1', 'test2'],
          repeat_count=20) +
      api.post_process(
          verify_log_fields,
          {'pass_fail_counts': {
              'test_common.Test1': {
                  'pass_count': 1,
                  'fail_count': 2},
              'test1.Test1': {
                  'pass_count': 1,
                  'fail_count': 0},
              'test1.Test2': {
                  'pass_count': 1,
                  'fail_count': 0},
              'test1.Test3': {
                  'pass_count': 0,
                  'fail_count': 0}}}) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('override_compile_targets') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          override_compile_targets=['base_unittests_run'])
  )

  yield (
      api.test('chartjson') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          perf_id='test-perf-id',
          results_url='https://example/url') +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2)
          + api.test_utils.canned_isolated_script_output(
              passing=True, swarming=True,
              shards=2, isolated_script_passing=True,
              output_chartjson=True,
              use_json_test_format=True),
          retcode=0)
  )

  # Uses simplified json
  # https://crbug.com/704066
  yield (
      api.test('chartjson_simplified_ignore_task_failure') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          perf_id='test-perf-id',
          results_url='https://example/url',
          ignore_task_failure=True) +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2)
          + api.test_utils.canned_isolated_script_output(
              passing=False, swarming=True,
              shards=2, isolated_script_passing=False, valid=True,
              output_chartjson=True))
  )

  yield (
      api.test('chartjson_ignore_task_failure') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          perf_id='test-perf-id',
          results_url='https://example/url',
          ignore_task_failure=True) +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2)
          + api.test_utils.canned_isolated_script_output(
              passing=False, swarming=True,
              shards=2, isolated_script_passing=False,
              output_chartjson=True, use_json_test_format=True))
  )

  # Uses simplied json
  # https://crbug.com/704066
  yield (
      api.test('chartjson_invalid') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          perf_id='test-perf-id',
          results_url='https://example/url') +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2)
          + api.test_utils.canned_isolated_script_output(
              passing=True, swarming=True,
              shards=2, isolated_script_passing=True, valid=False,
              output_chartjson=True),
          retcode=0)
  )

  yield (
      api.test('chartjson_max_failures') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          perf_id='test-perf-id',
          results_url='https://example/url') +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2)
          + api.test_utils.canned_isolated_script_output(
              passing=True, swarming=True,
              shards=2, isolated_script_passing=True,
              output_chartjson=True, use_json_test_format=True),
          retcode=102)
  )

  yield (
      api.test('chartjson_no_results') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          perf_id='test-perf-id',
          results_url='https://example/url')
  )

  yield (
      api.test('chartjson_no_results_failure') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          perf_id='test-perf-id',
          results_url='https://example/url') +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)', retcode=1)
  )

  yield (
      api.test('chartjson_not_uploading') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456) +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2)
          + api.test_utils.canned_isolated_script_output(
              passing=True, swarming=True,
              shards=2, isolated_script_passing=True,
              output_chartjson=True, use_json_test_format=True),
          retcode=0)
  )

  yield (
      api.test('chartjson_disabled') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          perf_id='test-perf-id',
          results_url='https://example/url') +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2)
          + api.test_utils.canned_isolated_script_output(
              passing=True, swarming=True,
              shards=2, isolated_script_passing=True,
              output_chartjson=True, benchmark_enabled=False,
              use_json_test_format=True),
          retcode=0)
  )

  # Uses simplied json
  # https://crbug.com/704066

  yield (
      api.test('chartjson_simplified_disabled') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          perf_id='test-perf-id',
          results_url='https://example/url') +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2)
          + api.test_utils.canned_isolated_script_output(
              passing=True, swarming=True,
              shards=2, isolated_script_passing=True, valid=True,
              output_chartjson=True, benchmark_enabled=False),
          retcode=0)
  )

  yield (
      api.test('histograms') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp='refs/heads/master@{#123456}',
          got_webrtc_revision='ffffffffffffffffffffffffffffffffffffffff',
          got_v8_revision='ffffffffffffffffffffffffffffffffffffffff',
          perf_id='test-perf-id',
          perf_dashboard_machine_group='ChromePerf',
          results_url='https://example/url') +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2) +
          api.test_utils.canned_isolated_script_output(
              passing=True, swarming=True,
              shards=2, isolated_script_passing=True,
              output_chartjson=True, benchmark_enabled=True,
              use_json_test_format=True, output_histograms=True) +
          api.swarming.merge_script_log_file('Merge succesfully'),
          retcode=0) +
      api.runtime(is_luci=True, is_experimental=False)
  )

  yield (
      api.test(
          'histograms_LUCI_missing_perf_dashboard_machine_group_property') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp='refs/heads/master@{#123456}',
          got_webrtc_revision='ffffffffffffffffffffffffffffffffffffffff',
          got_v8_revision='ffffffffffffffffffffffffffffffffffffffff',
          perf_id='test-perf-id',
          results_url='https://example/url') +
      api.override_step_data(
          'base_unittests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2)
          + api.test_utils.canned_isolated_script_output(
              passing=True, swarming=True,
              shards=2, isolated_script_passing=True,
              output_chartjson=True, benchmark_enabled=True,
              use_json_test_format=True, output_histograms=True),
          retcode=0)
      + api.runtime(is_luci=True, is_experimental=False)
  )

  yield (
      api.test('dimensions_windows') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          dimensions={'gpu': '8086', 'os': 'Windows'})
  )

  yield (
      api.test('dimensions_mac') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          dimensions={'gpu': '8086', 'os': 'Mac'})
  )

  yield (
      api.test('dimensions_mac_hidpi') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          dimensions={'gpu': '8086', 'os': 'Mac', 'hidpi': '1'})
  )

  yield (
      api.test('dimensions_android') +
      api.properties.generic(
          mastername='chromium.android',
          buildername='Lollipop Phone Tester') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          dimensions={
              'device_type': 'hammerhead',
              'device_os': 'LOL123',
              'os': 'Android'
          }
      )
  )

  yield (
      api.test('invalid_test_results') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests') +
      api.properties(
          buildnumber=123,
          swarm_hashes={
            'webkit_layout_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          git_revision='test_sha',
          version='test-version',
          got_revision_cp=123456,
          test_filter=['test1', 'test2'],
          repeat_count=20) +
      api.override_step_data(
          'webkit_layout_tests on Intel GPU on Linux (with patch)',
          api.swarming.canned_summary_output(2) +
          api.test_utils.m.json.output(None, 255)) +
      api.post_process(verify_log_fields, {'pass_fail_counts': {}}) +
      api.post_process(post_process.DropExpectation)
  )

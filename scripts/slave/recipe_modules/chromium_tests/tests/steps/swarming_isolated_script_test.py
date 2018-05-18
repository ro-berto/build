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


def RunSteps(api):
  api.chromium.set_build_properties({
      'got_webrtc_revision': 'webrtc_sha',
      'got_v8_revision': 'v8_sha',
  })
  api.chromium.set_config('chromium')

  bot_config_object = api.chromium_tests.create_bot_config_object(
      api.properties['mastername'], api.properties['buildername'])
  api.chromium_tests.configure_build(bot_config_object)
  api.chromium_tests.prepare_checkout(bot_config_object)

  test_repeat_count = api.properties.get('repeat_count')
  test_name = 'webkit_layout_tests' if test_repeat_count else 'base_unittests'
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
      dimensions=api.properties.get('dimensions', {'gpu': '8086'}))

  if test_repeat_count:
      test.test_options = api.chromium_tests.steps.TestOptions(
          test_filter=api.properties.get('test_filter'),
          repeat_count=test_repeat_count,
          retry_limit=0,
          run_disabled=bool(test_repeat_count)
      )

  try:
    test.pre_run(api, 'with patch')
    test.run(api, 'with patch')
    test.post_run(api, 'with patch')

    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api),
        'uses_local_devices: %r' % test.uses_local_devices,
        'uses_isolate: %r' % test.uses_isolate,
    ]

    if test_repeat_count:
        api.step.active_result.presentation.logs['details'].append(
            'pass_fail_counts: %r' % test.pass_fail_counts('with patch')
        )

  finally:
    if api.properties.get('run_without_patch'):
      test._only_retry_failed_tests = True

      test.pre_run(api, 'without patch')
      test.run(api, 'without patch')
      test.post_run(api, 'without patch')


def GenTests(api):
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
      api.post_process(post_process.Filter('[trigger] base_unittests on Intel GPU on Linux (without patch)'))
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
          repeat_count=20)
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
          api.swarming.canned_summary_output(2)
          + api.test_utils.canned_isolated_script_output(
              passing=True, swarming=True,
              shards=2, isolated_script_passing=True,
              output_chartjson=True, benchmark_enabled=True,
              use_json_test_format=True, output_histograms=True),
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

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

  test = api.chromium_tests.steps.SwarmingIsolatedScriptTest(
      'base_unittests',
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

  test.pre_run(api, '')
  test.run(api, '')
  test.post_run(api, '')

  api.step('details', [])
  api.step.active_result.presentation.logs['details'] = [
      'compile_targets: %r' % test.compile_targets(api),
      'uses_local_devices: %r' % test.uses_local_devices,
      'uses_swarming: %r' % test.uses_swarming,
  ]


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
          'base_unittests on Intel GPU on Linux',
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
          'base_unittests on Intel GPU on Linux',
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
          'base_unittests on Intel GPU on Linux',
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
          'base_unittests on Intel GPU on Linux',
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
          'base_unittests on Intel GPU on Linux',
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
      api.override_step_data('base_unittests on Intel GPU on Linux', retcode=1)
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
          'base_unittests on Intel GPU on Linux',
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
          'base_unittests on Intel GPU on Linux',
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
          'base_unittests on Intel GPU on Linux',
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
          'base_unittests on Intel GPU on Linux',
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
          'base_unittests on Intel GPU on Linux',
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

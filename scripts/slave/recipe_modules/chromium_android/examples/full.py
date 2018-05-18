# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
    'adb',
    'build',
    'chromium',
    'chromium_android',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
]

BUILDERS = freeze({
    'basic_builder': {
        'target': 'Release',
        'build': True,
    },
    'restart_usb_builder': {
        'restart_usb': True,
        'target': 'Release',
        'build': True,
    },
    'coverage_builder': {
        'coverage': True,
        'target': 'Debug',
        'build': True,
    },
    'tester': {},
    'perf_runner': {
        'perf_config': 'sharded_perf_tests.json',
    },
    'perf_runner_user_build': {
        'perf_config': 'sharded_perf_tests.json',
        'skip_wipe': True,
    },
    'perf_runner_disable_location': {
        'perf_config': 'sharded_perf_tests.json',
        'disable_location': True,
    },
    'perf_runner_allow_low_battery': {
        'perf_config': 'sharded_perf_tests.json',
        'min_battery_level': 50,
    },
    'perf_adb_vendor_keys': {
        'adb_vendor_keys': True,
    },
    'perf_runner_allow_high_battery_temp': {
        'perf_config': 'sharded_perf_tests.json',
        'max_battery_temp': 500,
    },
    'gerrit_try_builder': {
        'build': True,
        'skip_wipe': True,
    },
    'webview_tester': {
        'android_apply_config': ['remove_all_system_webviews'],
    },
    'slow_tester': {
        'timeout_scale': 2,
    },
    'downgrade_install_tester': {
        'specific_install': True,
        'downgrade': True,
    },
    'keep_data_install_tester': {
        'specific_install': True,
        'keep_data': True,
    },
    'no_strict_mode_tester': {
        'strict_mode': 'off',
    },
    'resource_size_builder': {
        'resource_size': True,
    },
    'webview_cts': {
        'run_webview_cts': True,
    },
    'device_flags_builder': {
        'device_flags': 'device_flags_file',
    },
    'no_cache_builder': {
        'use_git_cache': False,
    },
    'json_results_file': {
        'json_results_file': 'json_results_file',
    },
    'result_details': {
        'result_details': True,
        'store_tombstones': True,
    },
    'upload_archives_to_bucket': {
      'perf_config': 'sharded_perf_tests.json',
      'archives_bucket': 'my-bucket',
    },
    'timestamp_as_point_id': {
      'perf_config': 'sharded_perf_tests.json',
      'timestamp_as_point_id': True
    },
    'telemetry_browser_tests_tester': {
        'run_telemetry_browser_tests': True,
    },
    'use_devil_adb': {
      'android_apply_config': ['use_devil_adb'],
    },
    'remove_system_vrcore': {
      'android_apply_config': ['remove_system_vrcore'],
    },
    'stackwalker': {
      'run_stackwalker': True,
    },
    'asan': {
      'chromium_apply_config': ['chromium_asan'],
    }
})

from recipe_engine.recipe_api import Property

PROPERTIES = {
  'buildername': Property(),
}

def RunSteps(api, buildername):
  config = BUILDERS[buildername]

  api.chromium_android.configure_from_properties(
      'base_config',
      REPO_URL='svn://svn.chromium.org/chrome/trunk/src',
      REPO_NAME='src/repo',
      INTERNAL=True,
      BUILD_CONFIG='Release')

  api.chromium_android.c.get_app_manifest_vars = True
  api.chromium_android.c.coverage = config.get('coverage', False)
  api.chromium_android.c.asan_symbolize = True

  if config.get('adb_vendor_keys'):
    api.chromium.c.env.ADB_VENDOR_KEYS = api.path['start_dir'].join('.adb_key')

  for c in config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)

  for c in config.get('android_apply_config', []):
    api.chromium_android.apply_config(c)

  api.chromium_android.init_and_sync(
      use_bot_update=False, use_git_cache=config.get('use_git_cache', True))

  if config.get('build', False):
    api.chromium.ensure_goma()
  api.chromium.runhooks()
  api.chromium_android.run_tree_truth(additional_repos=['foo'])
  assert 'MAJOR' in api.chromium.get_version()

  api.chromium_android.host_info()

  if config.get('build', False):
    api.chromium.compile(use_goma_module=True)
    api.chromium_android.make_zip_archive(
        'zip_build_product', 'archive.zip', include_filters=['*.apk'],
        exclude_filters=['*.so', '*.a'])
  else:
    api.chromium_android.download_build('build-bucket',
                                        'build_product.zip')
  api.chromium_android.git_number()

  if config.get('specific_install'):
    api.chromium_android.adb_install_apk(
        'Chrome.apk',
        devices=['abc123'],
        allow_downgrade=config.get('downgrade', False),
        keep_data=config.get('keep_data', False),
    )

  api.adb.root_devices()
  api.chromium_android.spawn_logcat_monitor()

  failure = False
  try:
    # TODO(luqui): remove redundant cruft, need one consistent API.
    api.chromium_android.device_status_check()

    api.path.mock_add_paths(api.chromium_android.known_devices_file)
    api.chromium_android.device_status_check(
      restart_usb=config.get('restart_usb', False))

    api.chromium_android.provision_devices(
        skip_wipe=config.get('skip_wipe', False),
        disable_location=config.get('disable_location', False),
        min_battery_level=config.get('min_battery_level'),
        max_battery_temp=config.get('max_battery_temp'),
        reboot_timeout=1800)

    api.chromium_android.common_tests_setup_steps(skip_wipe=True)

  except api.step.StepFailure as f:
    failure = f

  api.chromium_android.monkey_test()

  try:
    if config.get('perf_config'):
      api.chromium_android.run_sharded_perf_tests(
          config=config.get('perf_config'),
          upload_archives_to_bucket=config.get('archives_bucket'),
          timestamp_as_point_id=config.get('timestamp_as_point_id', False))
  except api.step.StepFailure as f:
    failure = f
  api.chromium_android.run_instrumentation_suite(
      name='WebViewInstrumentationTest',
      apk_under_test=api.chromium_android.apk_path(
        'WebViewInstrumentation.apk'),
      test_apk=api.chromium_android.apk_path('WebViewInstrumentationTest.apk'),
      flakiness_dashboard='test-results.appspot.com',
      annotation='SmallTest',
      except_annotation='FlakyTest',
      screenshot=True,
      timeout_scale=config.get('timeout_scale'),
      strict_mode=config.get('strict_mode'),
      additional_apks=['Additional.apk'],
      device_flags=config.get('device_flags'),
      json_results_file=config.get('json_results_file'),
      result_details=config.get('result_details'),
      store_tombstones=config.get('store_tombstones'))
  api.chromium_android.run_test_suite(
      'unittests',
      result_details=config.get('result_details'),
      store_tombstones=config.get('store_tombstones'),
      tool='asan')
  if not failure:
      api.chromium_android.run_bisect_script(extra_src='test.py',
                                             path_to_config='test.py')

  if config.get('resource_size'):
    api.chromium_android.resource_sizes(
        apk_path=api.chromium_android.apk_path('Example.apk'),
        chartjson_file=True)
    api.chromium_android.supersize_archive(
        apk_path=api.chromium_android.apk_path('Example.apk'),
        size_path=api.chromium_android.apk_path('Example.apk.size'))

  if config.get('run_webview_cts'):
    api.chromium_android.run_webview_cts(
        android_platform='L',
        arch='arm64',
        command_line_args=['--webview_arg_1', '--webview_arg_2'],
        result_details=True)

  if config.get('run_telemetry_browser_tests'):
    api.chromium_android.run_telemetry_browser_test('PopularUrlsTest')

  api.chromium_android.logcat_dump()
  api.chromium_android.stack_tool_steps()
  if config.get('coverage', False):
    api.chromium_android.coverage_report()

  if config.get('run_stackwalker'):
    chrome_breakpad_binary = api.path['checkout'].join(
        'out', api.chromium.c.BUILD_CONFIG, 'lib.unstripped', 'libchrome.so')
    webview_breakpad_binary = api.path['checkout'].join(
        'out', api.chromium.c.BUILD_CONFIG, 'lib.unstripped',
        'libwebviewchromium.so')
    dump_syms_binary = api.path['checkout'].join(
        'out', api.chromium.c.BUILD_CONFIG, 'dump_syms')
    microdump_stackwalk_binary = api.path['checkout'].join(
        'out', api.chromium.c.BUILD_CONFIG, 'microdump_stackwalk')
    api.path.mock_add_paths(chrome_breakpad_binary)
    api.path.mock_add_paths(webview_breakpad_binary)
    api.path.mock_add_paths(dump_syms_binary)
    api.path.mock_add_paths(microdump_stackwalk_binary)

    api.chromium_android.common_tests_final_steps(
        checkout_dir=api.path['checkout'])


  if failure:
    # pylint: disable=raising-bad-type
    raise failure

def GenTests(api):
  def properties_for(buildername):
    return api.properties.generic(
        buildername=buildername,
        bot_id='tehslave',
        repo_name='src/repo',
        issue='123456789',
        patchset='1',
        rietveld='http://rietveld.example.com',
        repo_url='svn://svn.chromium.org/chrome/trunk/src',
        revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
        internal=True)

  for buildername in BUILDERS:
    yield api.test('%s_basic' % buildername) + properties_for(buildername)

  yield (api.test('tester_no_devices_during_recovery') +
         properties_for('tester') +
         api.step_data('device_recovery', retcode=1))

  yield (api.test('tester_no_devices_during_status') +
         properties_for('tester') +
         api.step_data('device_status', retcode=1))

  yield (api.test('tester_other_device_failure_during_recovery') +
         properties_for('tester') +
         api.step_data('device_recovery', retcode=2))

  yield (api.test('tester_other_device_failure_during_status') +
         properties_for('tester') +
         api.step_data('device_status', retcode=2))

  yield (api.test('tester_with_step_warning') +
         properties_for('tester') +
         api.step_data('unittests', retcode=88))

  yield (api.test('tester_failing_host_info') +
         properties_for('tester') +
         api.step_data(
             'Host Info',
             api.json.output({'failures': ['foo', 'bar']}),
             retcode=1))

  yield (api.test('tester_blacklisted_devices') +
         properties_for('tester') +
         api.override_step_data('provision_devices',
                                api.json.output(['abc123', 'def456'])))

  yield (api.test('tester_offline_devices') +
         properties_for('tester') +
         api.override_step_data('device_status',
                                api.json.output([{}, {}])))

  yield (api.test('perf_tests_failure') +
      properties_for('perf_runner') +
      api.step_data('perf_test.foo', retcode=1))

  yield (api.test('perf_tests_infra_failure') +
      properties_for('perf_runner') +
      api.step_data('perf_test.foo', retcode=87))

  yield (api.test('perf_tests_reference_failure') +
      properties_for('perf_runner') +
      api.step_data('perf_test.foo.reference', retcode=1))

  yield (api.test('perf_tests_infra_reference_failure') +
      properties_for('perf_runner') +
      api.step_data('perf_test.foo.reference', retcode=87))

  yield (api.test('gerrit_refs') +
      api.properties.generic(
        buildername='gerrit_try_builder',
        bot_id='testslave',
        repo_name='src/repo',
        issue='123456789',
        patchset='1',
        rietveld='http://rietveld.example.com',
        repo_url='svn://svn.chromium.org/chrome/trunk/src',
        revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
        internal=True, **({'event.patchSet.ref':'refs/changes/50/176150/1'})))

  yield (api.test('tombstones_m53') +
         properties_for('tester') +
         api.chromium.override_version(major=53))

  yield (api.test('telemetry_browser_tests_failures') +
         properties_for('telemetry_browser_tests_tester') +
         api.override_step_data('Run telemetry browser_test PopularUrlsTest',
             api.json.output({'successes': ['passed_test1', 'passed_test2'],
                              'failures': ['failed_test_1', 'failed_test_2']}),
             retcode=1))

  yield (api.test('upload_result_details_failures') +
         properties_for('result_details') +
         api.override_step_data('unittests: generate result details',
                                retcode=1))

  yield (api.test('asan_setup_failure') +
         properties_for('asan') +
         api.override_step_data('Set up ASAN on devices.wait_for_devices',
                                retcode=87))

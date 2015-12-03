# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for running SystemWebViewShell instrumentation layout tests using
system WebView.
"""

from recipe_engine.types import freeze

DEPS = [
  'adb',
  'bot_update',
  'chromium',
  'chromium_android',
  'gclient',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'test_utils',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

WEBVIEW_APK = 'SystemWebView.apk'

WEBVIEW_SHELL_APK = 'SystemWebViewShell.apk'

INSTRUMENTATION_TESTS = freeze([
  {
    'test': 'SystemWebViewShellLayoutTest',
    'gyp_target': 'system_webview_shell_layout_test_apk',
    'test_apk': 'SystemWebViewShellLayoutTest.apk',
    'kwargs': {
      'install_apk': {
        'package': 'org.chromium.webview_shell.test',
        'apk': 'SystemWebViewShellLayoutTest.apk'
      },
      'isolate_file_path':
        'android_webview/system_webview_shell_test_apk.isolate',
    },
  },
])


def RunSteps(api):
  api.chromium_android.configure_from_properties('webview_perf',
                                                 REPO_NAME='src',
                                                 REPO_URL=REPO_URL,
                                                 INTERNAL=False,
                                                 BUILD_CONFIG='Release')

  # Sync code.
  api.gclient.set_config('perf')
  api.gclient.apply_config('android')
  api.bot_update.ensure_checkout(force=True)
  api.chromium_android.clean_local_files()

  # Gyp the chromium checkout.
  api.chromium.runhooks()

  # Build the WebView apk, WebView shell, WebView shell layout test apk
  # and Android testing tools.
  api.chromium.compile(targets=['system_webview_apk',
                                'system_webview_shell_apk',
                                'system_webview_shell_layout_test_apk',
                                'android_tools'])

  api.chromium_android.spawn_logcat_monitor()
  api.chromium_android.device_status_check()
  api.chromium_android.provision_devices(
      min_battery_level=95, disable_network=True, disable_java_debug=True,
      reboot_timeout=180, remove_system_webview=True)

  # Install system WebView.
  api.chromium_android.adb_install_apk(WEBVIEW_APK)

  # Install system WebView shell
  api.chromium_android.adb_install_apk(WEBVIEW_SHELL_APK)

  api.adb.list_devices()

  # Run the instrumentation tests from the package.
  with api.step.defer_results():
    for suite in INSTRUMENTATION_TESTS:
      run_instrumentation_test(api, suite)

    api.chromium_android.logcat_dump()
    api.chromium_android.stack_tool_steps()
    api.chromium_android.test_report()

def run_instrumentation_test(api, suite):
  mock_test_results = {
    'per_iteration_data': [{'TestA': [{'status': 'SUCCESS'}]},
                           {'TestB': [{'status': 'FAILURE'}]}]
  }
  try:
    json_results_file = api.json.output(add_json_log=False)
    api.chromium_android.run_instrumentation_suite(
        suite['test'],
        test_apk=api.chromium_android.apk_path(suite['test_apk']),
        json_results_file=json_results_file, verbose=True,
        step_test_data=lambda: api.json.test_api.output(mock_test_results),
        **suite.get('kwargs', {}))
  finally:
    step_result = api.step.active_result
    try:
      json_results = step_result.json.output
      test_results = {test_name: test_data[0]['status']
                      for result_dict in json_results['per_iteration_data']
                      for test_name, test_data in result_dict.iteritems()}
      failures = sorted(
          [test_name for test_name, test_status in test_results.iteritems()
           if test_status not in ['SUCCESS', 'SKIPPED']])
    except Exception:  # pragma: no cover
      failures = None
    step_result.presentation.step_text += api.test_utils.format_step_text(
        [['failures:', failures]])


def GenTests(api):
  yield (api.test('basic') +
      api.properties.scheduled())

  yield (
      api.test('test_failure') +
      api.properties.scheduled() +
      api.step_data(
          'Instrumentation test SystemWebViewShellLayoutTest', retcode=1))

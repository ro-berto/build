# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Performance testing for the WebView.
"""

DEPS = [
  'adb',
  'bot_update',
  'chromium',
  'chromium_android',
  'gclient',
  'json',
  'path',
  'properties',
  'python',
  'step',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

PERF_TESTS = {
  "steps": {
    "sunspider": {
      "cmd": "tools/perf/run_benchmark" \
             " -v" \
             " --browser=android-webview" \
             " --extra-browser-args=--spdy-proxy-origin" \
             " --show-stdout sunspider",
      "device_affinity": 0,
    },
    "page_cycler.bloat": {
      "cmd": "tools/perf/run_benchmark" \
             " -v" \
             " --browser=android-webview" \
             " --extra-browser-args=--spdy-proxy-origin" \
             " --show-stdout page_cycler.bloat",
      "device_affinity": 1,
    },
  },
  "version": 1,
}

WEBVIEW_APK = 'SystemWebView.apk'
WEBVIEW_PACKAGE = 'com.android.webview'

TELEMETRY_SHELL_APK = 'AndroidWebViewTelemetryShell.apk'
TELEMETRY_SHELL_PACKAGE = 'org.chromium.telemetry_shell'

BUILDER = {
  'perf_id': 'android-webview',
  'num_device_shards': 2,
}

def GenSteps(api):
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
  api.chromium_android.runhooks()

  # Build the WebView apk, WebView shell and Android testing tools.
  api.chromium.compile(targets=['system_webview_apk',
                                'android_webview_telemetry_shell_apk',
                                'android_tools'])

  api.chromium_android.spawn_logcat_monitor()
  api.chromium_android.device_status_check()
  api.chromium_android.provision_devices()

  # Install WebView
  api.chromium_android.adb_install_apk(WEBVIEW_APK, WEBVIEW_PACKAGE)

  # Install the telemetry shell.
  api.chromium_android.adb_install_apk(TELEMETRY_SHELL_APK,
                                       TELEMETRY_SHELL_PACKAGE)

  # TODO(hjd) Start using api.chromium.list_perf_tests
  try:
    api.chromium_android.run_sharded_perf_tests(
      config=api.json.input(data=PERF_TESTS),
      perf_id=BUILDER['perf_id'])
  finally:
    api.chromium_android.logcat_dump()
    api.chromium_android.stack_tool_steps()
    api.chromium_android.test_report()


def GenTests(api):
  yield api.test('basic') + api.properties.scheduled()

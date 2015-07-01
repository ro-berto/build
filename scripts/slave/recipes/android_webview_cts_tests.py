# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for running WebView CTS using system WebView.
"""

#from urllib2 import urlopen, URLError, HTTPError

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

# TODO(hush): Put the CTS zip file in the google storage
# and use gs_utils to download.
CTS_FILE_URL = "https://dl.google.com/dl/android/cts/android-cts-5.1_r1-linux_x86-arm.zip"
CTS_FILE_NAME = "android-cts-5.1_r1-linux_x86-arm.zip"

WEBVIEW_APK = 'SystemWebView.apk'
WEBVIEW_PACKAGE = 'com.android.webview'

def RunSteps(api):
  api.chromium_android.configure_from_properties('main_builder',
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

  # Build the WebView apk
  api.chromium.compile(targets=['system_webview_apk'])

  api.chromium_android.spawn_logcat_monitor()
  api.chromium_android.device_status_check()
  api.chromium_android.provision_devices(
      min_battery_level=95, disable_network=True, disable_java_debug=True,
      reboot_timeout=180)

  api.adb.list_devices()
  # Install WebView
  api.chromium_android.adb_install_apk(WEBVIEW_APK, WEBVIEW_PACKAGE)

  cts_dir = api.path['slave_build'].join('tmp', 'cts')
  cts_zip_path = cts_dir.join(CTS_FILE_NAME)

  # Step 1 Download cts to build bot dir to tmp/cts.
  api.step('Download Cts', ['curl', CTS_FILE_URL, '-o',
      cts_dir.join(CTS_FILE_NAME), '-z', cts_zip_path, '--create-dirs'])

  # Step 2 Extract cts zip file
  api.step('Extract Cts', ['unzip', '-o', CTS_FILE_NAME, '-d', './'],
      cwd=cts_dir)

  # Step 3 Run cts tests
  adb_path = api.path['slave_build'].join('src', 'third_party', 'android_tools',
      'sdk', 'platform-tools')
  env = {'PATH': api.path.pathsep.join([str(adb_path), '%(PATH)s'])}
  api.step('Run Cts', [cts_dir.join('android-cts', 'tools', 'cts-tradefed'),
      'run', 'cts', '-p', 'android.webkit'], env=env)

  api.chromium_android.logcat_dump()
  api.chromium_android.stack_tool_steps()
  api.chromium_android.test_report()

def GenTests(api):
  yield api.test('android_webview_cts_tests') + api.properties.scheduled()

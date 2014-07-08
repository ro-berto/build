# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_android',
    'gclient',
    'step',
    'path',
    'properties',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

PERF_ANDROID = {
  'bucket': 'chrome-perf',
  'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                             % api.properties['parent_revision']),
}

BUILDERS = {
  'android_nexus5_oilpan_perf': {
    'bucket': 'chromium-android',
    'path': lambda api: (
      '%s/build_product_%s.zip' % (
            api.properties['parent_buildername'],
            api.properties['parent_revision'])),
  },
  'Android Nexus4 Perf': PERF_ANDROID,
  'Android Nexus5 Perf': PERF_ANDROID,
  'Android Nexus7v2 Perf': PERF_ANDROID,
  'Android Nexus10 Perf': PERF_ANDROID,
  'Android GN Perf': PERF_ANDROID,
}

def GenSteps(api):
  buildername = api.properties['buildername']
  builder = BUILDERS[buildername]
  api.chromium_android.configure_from_properties('base_config',
                                                 REPO_NAME='src',
                                                 REPO_URL=REPO_URL,
                                                 INTERNAL=False,
                                                 BUILD_CONFIG='Release')
  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')

  yield api.chromium_android.init_and_sync()

  yield api.chromium_android.download_build(bucket=builder['bucket'],
    path=builder['path'](api))

  yield api.chromium_android.spawn_logcat_monitor()
  yield api.chromium_android.device_status_check()
  yield api.chromium_android.provision_devices()

  yield api.chromium_android.adb_install_apk(
      'ChromeShell.apk',
      'org.chromium.chrome.shell')

  tests_json_file = api.path['checkout'].join('out', 'perf-tests.json')
  yield api.chromium_android.list_perf_tests(browser='android-content-shell',
    json_output_file=tests_json_file)
  yield api.chromium_android.run_sharded_perf_tests(
      config=tests_json_file,
      perf_id=buildername)

  yield api.chromium_android.logcat_dump()
  yield api.chromium_android.stack_tool_steps()
  yield api.chromium_android.test_report()

  yield api.chromium_android.cleanup_build()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)

def GenTests(api):
  for buildername in BUILDERS:
    yield (
        api.test('test_%s' % _sanitize_nonalpha(buildername)) +
        api.properties.generic(
            repo_name='src',
            repo_url=REPO_URL,
            buildername=buildername,
            parent_buildername='parent_buildername',
            parent_buildnumber='1729',
            parent_revision='deadbeef',
            revision='deadbeef',
            slavename='slavename',
            target='Release')
    )

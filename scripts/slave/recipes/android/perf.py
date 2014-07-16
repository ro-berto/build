# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'adb',
    'bot_update',
    'chromium_android',
    'gclient',
    'json',
    'step',
    'path',
    'properties',
    'step_history',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

BUILDERS = {
  'android_nexus5_oilpan_perf': {
    'perf_id': 'android-nexus5-oilpan',
    'bucket': 'chromium-android',
    'path': lambda api: (
      '%s/build_product_%s.zip' % (
            api.properties['parent_buildername'],
            api.properties['parent_revision'])),
    'num_device_shards': 1,
  },
  'Android Nexus4 Perf': {
    'perf_id': 'android-nexus4',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
    'num_device_shards': 2,
  },
  'Android Nexus5 Perf': {
    'perf_id': 'android-nexus5',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
    'num_device_shards': 8,
  },
  'Android Nexus7v2 Perf': {
    'perf_id': 'android-nexus7v2',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
    'num_device_shards': 1,
  },
  'Android Nexus10 Perf': {
    'perf_id': 'android-nexus10',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
    'num_device_shards': 1,
  },
  'Android GN Perf': {
    'perf_id': 'android-gn',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
    'num_device_shards': 1,
  },
  'Android MotoE Perf': {
    'perf_id': 'android-motoe',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
    'num_device_shards': 1,
  },
}

def GenSteps(api):
  buildername = api.properties['buildername']
  builder = BUILDERS[buildername]
  api.chromium_android.configure_from_properties('base_config',
                                                 REPO_NAME='src',
                                                 REPO_URL=REPO_URL,
                                                 INTERNAL=False,
                                                 BUILD_CONFIG='Release')
  api.gclient.set_config('perf')
  api.gclient.apply_config('android')

  yield api.bot_update.ensure_checkout()
  api.path['checkout'] = api.path['slave_build'].join('src')

  yield api.chromium_android.download_build(bucket=builder['bucket'],
      path=builder['path'](api))

  # The directory extracted as src/full-build-linux and needs to be renamed to
  # src/out/Release
  # TODO(zty): remove the following once parent builder is zipping out/
  yield api.step(
      'rm out',
      ['rm', '-rf', api.path['checkout'].join('out')])
  yield api.step(
      'mkdir out',
      ['mkdir', '-p', api.path['checkout'].join('out')])
  yield api.step(
      'move build',
      ['mv', api.path['checkout'].join('full-build-linux'),
             api.path['checkout'].join('out','Release')])

  yield api.chromium_android.spawn_logcat_monitor()
  yield api.chromium_android.device_status_check(abort_on_failure=True)
  yield api.chromium_android.provision_devices(abort_on_failure=True)

  yield api.chromium_android.adb_install_apk(
      'ChromeShell.apk',
      'org.chromium.chrome.shell')

  # TODO(zty): remove this in favor of device_status_check
  yield api.adb.list_devices()
  yield api.chromium_android.list_perf_tests(
      browser='android-chrome-shell',
      num_device_shards=builder['num_device_shards'],
      devices=api.adb.devices[0:1])
  perf_tests = api.step_history['List Perf Tests'].json.output
  yield api.chromium_android.run_sharded_perf_tests(
      config=api.json.input(data=perf_tests),
      perf_id=builder['perf_id'])

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
            target='Release') +
        api.override_step_data('List adb devices', api.json.output([
          "014E1F310401C009", "014E1F310401C010"
          ]))
    )
  yield (api.test('device_status_check') +
      api.properties.generic(
          repo_name='src',
              repo_url=REPO_URL,
              buildername='Android GN Perf',
              parent_buildername='parent_buildername',
              parent_buildnumber='1729',
              parent_revision='deadbeef',
              revision='deadbeef',
              slavename='slavename',
              target='Release')
      + api.step_data('device_status_check', retcode=1))
  yield (api.test('provision_devices') +
      api.properties.generic(
          repo_name='src',
              repo_url=REPO_URL,
              buildername='Android GN Perf',
              parent_buildername='parent_buildername',
              parent_buildnumber='1729',
              parent_revision='deadbeef',
              revision='deadbeef',
              slavename='slavename',
              target='Release')
      + api.step_data('provision_devices', retcode=1))

# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_checkout',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'ios',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'webrtc'
]


def RunSteps(api):
  api.gclient.set_config('webrtc_ios')
  api.ios.host_info()
  api.webrtc.checkout()

  build_config_base_dir = api.path['checkout'].join(
      'webrtc',
      'build',
      'ios',
  )
  buildername = api.properties['buildername'].replace(' ', '_')
  api.ios.read_build_config(build_config_base_dir=build_config_base_dir,
                            buildername=buildername)
  mb_config_path = api.path['checkout'].join(
      'webrtc',
      'build',
      'mb_config.pyl',
  )
  gyp_script = api.path['checkout'].join(
      'webrtc',
      'build',
      'gyp_webrtc.py',
  )
  if 'gyp' not in buildername.lower():
    api.ios.build(mb_config_path=mb_config_path, gyp_script=gyp_script)
    api.ios.test()
  else:
    mastername = api.properties['mastername']
    buildername = api.properties['buildername']
    api.chromium.runhooks()
    api.chromium.run_mb(mastername, buildername, mb_config_path=mb_config_path,
                        gyp_script=gyp_script)

def GenTests(api):
  yield (
    api.test('basic')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios debug',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
        'use_goma': '1',
      },
      'mb_type': 'gyp',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.0',
      'tests': [
        {
          'app': 'fake tests 1',
          'device type': 'fake device',
          'os': '8.0',
        },
        {
          'app': 'fake tests 2',
          'device type': 'fake device',
          'os': '7.1',
        },
      ],
    })
  )

  yield (
    api.test('gn_build')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
      },
      "gn_args": [
        "is_debug=true"
      ],
      "mb_type": "gn",
      'configuration': 'Debug',
      'sdk': 'iphoneos8.0',
      'tests': [
      ],
    })
  )

  yield (
    api.test('gyp_build')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios gyp',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
      },
      "gn_args": [
        "is_debug=true"
      ],
      "mb_type": "gn",
      'configuration': 'Debug',
      'sdk': 'iphoneos8.0',
      'tests': [
      ],
    })
  )

  yield (
    api.test('no_tests')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
        'use_goma': '1',
      },
      'mb_type': 'gyp',
      'configuration': 'Release',
      'sdk': 'iphoneos8.0',
      'tests': [
      ],
    })
  )

  yield (
    api.test('trybot')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
        'use_goma': '1',
      },
      'use_analyze': 'false',
      'mb_type': 'gyp',
      'configuration': 'Release',
      'sdk': 'iphoneos8.0',
      'tests': [
      ],
    })
  )

  yield (
    api.test('test_failure')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
      },
      'mb_type': 'gyp',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.0',
      'tests': [
        {
          'app': 'fake tests 1',
          'device type': 'fake device',
          'os': '8.0',
        },
        {
          'app': 'fake tests 2',
          'device type': 'fake device',
          'os': '7.1',
        },
      ],
    })
    + api.step_data(
      'fake tests 1 (fake device iOS 8.0)',
      retcode=1
    )
  )

  yield (
    api.test('infrastructure_failure')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
      },
      'mb_type': 'gyp',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.0',
      'tests': [
        {
          'app': 'fake tests 1',
          'device type': 'fake device',
          'os': '8.0',
        },
        {
          'app': 'fake tests 2',
          'device type': 'fake device',
          'os': '7.1',
        },
      ],
    })
    + api.step_data(
      'fake tests 1 (fake device iOS 8.0)',
      retcode=2,
    )
  )


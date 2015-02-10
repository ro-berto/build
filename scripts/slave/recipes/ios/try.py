# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'ios',
  'platform',
  'properties',
]

def GenSteps(api):
  api.ios.host_info()
  api.ios.checkout()

  # A try bot gets its config by reading a build config file as if it were
  # running on the main waterfall. This ensures try bots always match the
  # main waterfall config.
  api.ios.read_build_config(master_name='chromium.mac')
  api.ios.build()
  api.ios.test()

def GenTests(api):
  yield (
    api.test('basic')
    + api.platform('mac', 64)
    + api.properties(patch_url='patch url')
    + api.properties(
      buildername='ios',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
      },
      'compiler': 'xcodebuild',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.0',
      'tests': [
        {
          'app': 'fake tests',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
  )

  yield (
    api.test('parent')
    + api.platform('mac', 64)
    + api.properties(patch_url='patch url')
    + api.properties(
      buildername='ios',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'triggered by': 'parent',
      'tests': [
        {
          'app': 'fake tests',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
    + api.ios.make_test_build_config_for_parent({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
      },
      'compiler': 'xcodebuild',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.0',
    })
  )

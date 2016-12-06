# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'ios',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
]

def RunSteps(api):
  api.ios.checkout()
  api.ios.read_build_config()
  api.ios.build(
    default_gn_args_path='src/example/args.gn', setup_gn=True, use_mb=False)
  api.ios.test_swarming()

def GenTests(api):
  yield (
    api.test('basic')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.1',
      'bucket': 'mock-gcs-bucket',
      'tests': [
        {
          'app': 'fake test 1',
          'device type': 'fake device 1',
          'os': '8.1',
          'test args': [
            '--fake-arg-1',
            '--fake-arg-2',
          ],
        },
        {
          'include': 'fake include.json',
          'device type': 'fake device 1',
          'os': '8.1',
        },
        {
          'app': 'fake test 2',
          'device type': 'fake device 2',
          'os': '7.1',
        },
        {
          'include': 'fake include.json',
          'device type': 'fake device 2',
          'os': '7.1',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output('1.2.3'),
    )
    + api.path.exists(
        api.path['tmp_base'].join('0_tmp_2', '0'),
    )
  )

  yield (
    api.test('errors')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'configuration': 'Release',
      'sdk': 'iphoneos8.1',
      'tests': [
        {
          'app': 'fake test 1',
          'device type': 'fake device',
          'os': '8.1',
        },
        {
          'app': 'fake test 2',
          'device type': 'iPad Air',
          'os': '8.1',
        },
        {
          'app': 'fake test 3',
          'device type': 'fake device',
          'os': '8.1',
        },
        {
          'app': 'fake test 4',
          'device type': 'iPhone 5s',
          'os': '8.1',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output('1.2.3'),
    )
    + api.step_data(
        'isolate.generate 0.isolate.gen.json',
        retcode=1,
    )
    + api.step_data(
        'trigger.[trigger] fake test 4 (iPhone 5s iOS 8.1) on iOS-8.1',
        retcode=1,
    )
  )

  yield (
    api.test('test_failure')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.1',
      'tests': [
        {
          'app': 'fake test',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output('1.2.3'),
    )
    + api.override_step_data(
        'fake test (fake device iOS 8.1)',
        api.json.output({
          'shards': [{
            'exit_codes': [1],
            'state': 112,
          }],
        }),
        retcode=1,
    )
  )

  yield (
    api.test('infra_failure')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.1',
      'tests': [
        {
          'app': 'fake test',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output('1.2.3'),
    )
    + api.override_step_data(
        'fake test (fake device iOS 8.1)',
        api.json.output({
          'shards': [{
            'exit_codes': [2],
            'state': 112,
          }],
        }),
        retcode=1,
    )
  )

  yield (
    api.test('timed_out')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.1',
      'tests': [
        {
          'app': 'fake test',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output('1.2.3'),
    )
    + api.override_step_data(
        'fake test (fake device iOS 8.1)',
        api.json.output({
          'shards': [{
            'state': 64,
          }],
        }),
        retcode=1,
    )
  )

  yield (
    api.test('expired')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.1',
      'tests': [
        {
          'app': 'fake test',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output('1.2.3'),
    )
    + api.override_step_data(
        'fake test (fake device iOS 8.1)',
        api.json.output({
          'shards': [{
            'state': 48,
          }],
        }),
        retcode=1,
    )
  )

  yield (
    api.test('no_exit_code')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.1',
      'tests': [
        {
          'app': 'fake test',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output('1.2.3'),
    )
    + api.override_step_data(
        'fake test (fake device iOS 8.1)',
        api.json.output({
          'shards': [{
            'state': 112,
          }],
        }),
        retcode=1,
    )
  )

  yield (
    api.test('clobber')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      clobber=True,
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.1',
      'tests': [
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output('1.2.3'),
    )
  )

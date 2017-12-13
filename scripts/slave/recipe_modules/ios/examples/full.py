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
  'swarming',
]

def RunSteps(api):
  api.ios.checkout()
  api.ios.read_build_config()
  api.ios.build(
    default_gn_args_path='src/example/args.gn', setup_gn=True, use_mb=False)
  api.ios.upload()
  api.ios.test_swarming()

def GenTests(api):
  yield (
    api.test('basic')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'gn_args': [
        'is_debug=true',
        'target_cpu="x64"',
        'use_goma=true',
      ],
      'xcode version': '6.1.1',
      'bucket': 'mock-gcs-bucket',
      'upload': [
        {
          'artifact': 'Chrome.app',
        },
        {
          'artifact': 'Chrome.app.arm.breakpad',
          'symupload': 'https://clients2.google.com/cr/symbol',
        },
      ],
      'tests': [
        {
          'app': 'fake test 0',
          'device type': 'fake device 0',
          'os': '11.0',
          'sharding': 'ios/chrome/browser',
          'shard size': 2,
        },
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
          'app': 'fake test 2',
          'device type': 'fake device 2',
          'os': '8.1',
          'host os': 'Mac-10.12',
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
      'triggered bots': [
          'fake child 1',
          'fake child 2',
      ],
    })
    + api.ios.make_test_build_configs_for_children([
      {
        'tests': [
          {
            'app': 'fake child test 1',
            'device type': 'fake child device 1',
            'os': '8.1',
          },
        ],
      },
      {
        'tests': [
          {
            'include': 'fake include.json',
            'device type': 'fake child device 2',
            'os': '9.0',
          },
        ],
      },
    ])
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + api.path.exists(
        api.path['tmp_base'].join('0_tmp_2', '0'),
        api.path['tmp_base'].join('0_tmp_2', '0', 'full_results.json'),
        api.path['tmp_base'].join('0_tmp_2', '0', 'Documents', 'perf_result.json'),
    )
  )

  yield (
    api.test('errors')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=false',
        'target_cpu="arm64"',
      ],
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
        stdout=api.raw_io.output_text('1.2.3'),
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
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
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
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + api.step_data(
        'fake test (fake device iOS 8.1)',
        api.swarming.summary({
          'shards': [{
            'exit_codes': [1],
            'state': 112,
          }],
        }),
        retcode=1,
    )
  )

  yield (
    api.test('perf_test')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
      got_revision_cp='123456',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'tests': [
        {
          'app': 'fake test',
          'bot id': 'fake99-b1',
          'device type': 'fake device',
          'os': '8.1',
          'pool': 'fake-pool',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + api.path.exists(
        api.path['tmp_base'].join('0_tmp_2', '0', 'Documents', 'perf_result.json'),
    )
  )

  yield (
    api.test('infra_failure')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
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
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + api.step_data(
        'fake test (fake device iOS 8.1)',
        api.swarming.summary({
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
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
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
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + api.step_data(
        'fake test (fake device iOS 8.1)',
        api.swarming.summary({
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
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
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
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + api.step_data(
        'fake test (fake device iOS 8.1)',
        api.swarming.summary({
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
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
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
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + api.step_data(
        'fake test (fake device iOS 8.1)',
        api.swarming.summary({
          'shards': [{
            'state': 112,
          }],
        }),
        retcode=1,
    )
  )

  yield (
    api.test('is_debug_missing')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'target_cpu="x86"',
      ],
      'tests': [
      ],
    })
  )

  yield (
    api.test('target_cpu_missing')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
      ],
      'tests': [
      ],
    })
  )

  yield (
    api.test('clobber_checkout')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      clobber=True,
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'tests': [
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('clobber_build')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'clobber': True,
      'tests': [
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('fyi')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fyi',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
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
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('explain')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'explain': True,
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )


  yield (
    api.test('expiration_test')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '6.1.1',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'tests': [
        {
          'app': 'fake test',
          'bot id': 'fake99-b1',
          'device type': 'fake device',
          'os': '8.1',
          'pool': 'fake-pool',
          'expiration_time': 3600,
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
 )

  yield (
    api.test('xcode_build_version')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fyi',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode build version': '9a123',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'tests': [
        {
          'app': 'fake test',
          'device type': 'fake device',
          'os': '10.0',
        },
        {
          'app': 'fake test 2',
          'device type': 'fake device 2',
          'os': '11.0',
          'xcode build version': '9b456',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

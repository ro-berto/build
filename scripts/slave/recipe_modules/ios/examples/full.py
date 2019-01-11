# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'ios',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'swarming',
]

def RunSteps(api):
  api.ios.checkout()
  api.ios.read_build_config()
  api.ios.build(use_mb=False)
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
      'xcode build version': '9abc',
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
          'shard size': 2,
          'dimensions': [
            {
              'os': 'Mac-10.12',
              'pool': 'Chrome',
            },
            {
              'os': 'Mac-10.13',
              'pool': 'Chrome',
            }
          ],
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
          'shards': 4,
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
        api.path['cleanup'].join('0_1_tmp_3', '110000'),
        api.path['cleanup'].join('0_1_tmp_3', '110000', 'full_results.json'),
        api.path['cleanup'].join('0_2_tmp_4', '120000'),
        api.path['cleanup'].join('0_2_tmp_4', '120000', 'full_results.json'),
        api.path['cleanup'].join('1_tmp_5', '130000'),
        api.path['cleanup'].join('1_tmp_5', '130000', 'full_results.json'),
        api.path['cleanup'].join('1_tmp_5', '130000', 'Documents',
                                 'perf_result.json'),
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
      'xcode build version': '9abc',
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
        'isolate.generate 0.isolated.gen.json',
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
      'xcode build version': '9abc',
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
            'exit_code': 1,
            'state': 'COMPLETED',
          }],
        }),
        retcode=1,
    )
    + api.post_process(post_process.StatusFailure)
  )

  yield (
    api.test('test_failure_str_exit_code')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode build version': '9abc',
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
            'exit_code': '1',
            'state': 'COMPLETED',
          }],
        }),
        retcode=1,
    )
    + api.post_process(post_process.StatusFailure)
    + api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('test_failure_noninteger_str_exit_code')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode build version': '9abc',
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
            'exit_code': 'b',
            'state': 'COMPLETED',
          }],
        }),
        retcode=1,
    )
    + api.post_process(
        post_process.MustRun,
        'Unrecognized exit_code from swarming')
    + api.post_process(post_process.StatusFailure)
    + api.post_process(post_process.DropExpectation)
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
      'xcode build version': '9abc',
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
        api.path['cleanup'].join('0_tmp_2', '10000', 'Documents',
                                 'perf_result.json'),
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
      'xcode build version': '9abc',
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
            'exit_code': 2,
            'state': 'COMPLETED',
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
      'xcode build version': '9abc',
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
            'state': 'TIMED_OUT',
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
      'xcode build version': '9abc',
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
            'state': 'EXPIRED',
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
      'xcode build version': '9abc',
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
            'state': 'BOT_DIED',
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
      'xcode build version': '9abc',
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
      'xcode build version': '9abc',
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
      'xcode build version': '9abc',
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
      'xcode build version': '9abc',
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
      'xcode build version': '9abc',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'tests': [
        {
          'app': 'fake test',
          'device type': 'fake device',
          'os': '8.1',
          'priority': 199,
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
      'xcode build version': '9abc',
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
      'xcode build version': '9abc',
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
    api.test('max_runtime_test')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode build version': '9abc',
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
          'max runtime seconds': 7200,
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
 )

  xcode_build_version = (
    api.platform('mac', 64)
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
          'app': 'build-global xcode build version',
          'device type': 'fake device',
          'os': '10.0',
        },
        {
          'app': 'task-local xcode build version',
          'device type': 'fake device 2',
          'os': '11.0',
          'xcode build version': '9b456',
        },
        {
          'app': 'task-local xcode version',
          'device type': 'fake device 3',
          'os': '11.0',
          'xcode version': '9.2',
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
    +api.runtime(is_luci=False, is_experimental=False)
    + xcode_build_version
  )

  yield (
    api.test('xcode_build_version_luci')
    +api.runtime(is_luci=True, is_experimental=True)
    + xcode_build_version
  )

  yield (
    api.test('device_check_false')
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
        'target_cpu="arm64"',
      ],
      'device check': False,
      'tests': [
        {
          'app': 'build-global xcode build version',
          'device type': 'iPhone X',
          'os': '10.0',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('deprecate_xcode_version')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fyi',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': '8.0',
      'gn_args': [
        'is_debug=true',
        'target_cpu="arm64"',
      ],
      'device check': False,
      'tests': [
        {
          'app': 'build-global xcode version',
          'device type': 'iPhone X',
          'os': '10.0',
        },
        {
          'app': 'test-local xcode version',
          'device type': 'iPhone X',
          'os': '11.0',
          'xcode version': '9.0',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('use_wpr_tools')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fyi',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode build version': '9abc',
      'additional files': [
        'fake/file/path1/',
        'fake/file/path2/',
      ],
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'tests': [
        {
          'app': 'fake test',
          'device type': 'fake device',
          'os': '8.1',
          'replay package name': 'chromium/ios/autofill/recipe-and-replay-data',
          'replay package version': 'version:latest',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('xparallel_run_and_skip')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fyi',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode build version': '09a123',
      'additional files': [
        'fake/file/path1/',
        'fake/file/path2/',
      ],
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'tests': [
        {
          'xcode parallelization': True,
          'shards': 3,
          'app': 'fake test',
          'device type': 'fake device',
          'os': '12.0.1',
        },
        {
          'app': 'fake test2',
          'device type': 'fake device',
          'os': '12.0.1',
        }
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('use_trusted_cert')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fyi',
      bot_id='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode build version': '9abc',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'tests': [
        {
          'app': 'fake test',
          'device type': 'fake device',
          'os': '8.1',
          'use trusted cert': True,
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

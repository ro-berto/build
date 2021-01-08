# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import post_process

DEPS = [
    'chromium',
    'ios',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'chromium_swarming',
]

def RunSteps(api):
  api.ios.checkout()
  api.ios.read_build_config()
  api.ios.build(use_mb=False)
  api.ios.upload()
  api.ios.test_swarming()

def GenTests(api):
  BASIC_TEST_SUITES = [
    'fake test 0 (fake device 0 iOS 11.0) shard 0 (with patch)',
    'fake test 0 (fake device 0 iOS 11.0) shard 1 (with patch)',
    'fake test 0 (fake device 0 iOS 11.0) shard 2 (with patch)',
    'fake test 1 (fake device 1 iOS 8.1) (with patch)',
    'fake test 2 (fake device 2 iOS 8.1) (with patch) on Mac-10.12',
    'fake included test 1 (fake device 1 iOS 8.1) (with patch)',
    'fake included test 2 (fake device 1 iOS 8.1) (with patch)',
    'fake test 2 (fake device 2 iOS 7.1) (with patch)',
    'fake included test 1 (fake device 2 iOS 7.1) (with patch)',
    'fake included test 2 (fake device 2 iOS 7.1) (with patch)',
  ]

  def gen_basic(api):
    result = api.test(
        'basic',
        api.platform('mac', 64),
        api.chromium.ci_build(
            builder_group='chromium.fake',
            builder='ios',
            build_number=1,
            revision='HEAD',
        ),
        api.ios.make_test_build_config({
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
                {
                    'artifact':
                        'Chrome.app',
                    'upload_path':
                        'some_path/Webkit-{%revision%}-{%timestamp%}.zip'
                },
            ],
            'tests': [
                {
                    'app': 'fake test 0',
                    'device type': 'fake device 0',
                    'os': '11.0',
                    'swarming tasks': 3
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
        }),
        api.ios.make_test_build_configs_for_children([
            {
                'tests': [{
                    'app': 'fake child test 1',
                    'device type': 'fake child device 1',
                    'os': '8.1',
                },],
            },
            {
                'tests': [{
                    'include': 'fake include.json',
                    'device type': 'fake child device 2',
                    'os': '9.0',
                },],
            },
        ]),
        api.path.exists(
            api.path['cleanup'].join('0_1_tmp_3', '110000'),
            api.path['cleanup'].join('0_1_tmp_3', '110000',
                                     'full_results.json'),
            api.path['cleanup'].join('0_2_tmp_4', '120000'),
            api.path['cleanup'].join('0_2_tmp_4', '120000',
                                     'full_results.json'),
            api.path['cleanup'].join('1_tmp_5', '130000'),
            api.path['cleanup'].join('1_tmp_5', '130000', 'full_results.json'),
            api.path['cleanup'].join('1_tmp_5', '130000', 'Documents',
                                     'perf_result.json'),
        ),
    )

    for index, test in enumerate(BASIC_TEST_SUITES):
      result += api.step_data(
          test,
          api.ios.generate_test_results_placeholder(
              failure=False, swarming_number=index))

    result += api.post_process(post_process.StatusSuccess)
    return result

  yield gen_basic(api)

  yield api.test(
      'errors',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
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
      }),
      api.step_data(
          'isolate.generate 0.isolated.gen.json',
          retcode=1,
      ),
      api.step_data(
          'test_pre_run (with patch).[trigger] fake test 4 (iPhone 5s iOS 8.1) '
          '(with patch) on iOS-8.1',
          retcode=1,
      ),
  )

  yield api.test(
      'test_failure',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data('fake test (fake device iOS 8.1) (with patch)',
                    api.ios.generate_test_results_placeholder(failure=True)),
      api.post_process(post_process.StatusFailure),
  )

  yield api.test(
      'test_swarming_failure',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data(
          'fake test (fake device iOS 8.1) (with patch)',
          api.chromium_swarming.summary(None, {
              'shards': [{
                  'exit_code': 1,
                  'state': 'COMPLETED',
              }],
          })),
      api.post_process(post_process.StatusException),
  )

  yield api.test(
      'test_failure_str_exit_code',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data(
          'fake test (fake device iOS 8.1) (with patch)',
          api.chromium_swarming.summary(None, {
              'shards': [{
                  'exit_code': '1',
                  'state': 'COMPLETED',
              }],
          })),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'infra_failure',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data(
          'fake test (fake device iOS 8.1) (with patch)',
          api.chromium_swarming.summary(None, {
              'shards': [{
                  'exit_code': 2,
                  'state': 'COMPLETED',
              }],
          })),
  )

  yield api.test(
      'timed_out',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data(
          'fake test (fake device iOS 8.1) (with patch)',
          api.chromium_swarming.summary(None, {
              'shards': [{
                  'state': 'TIMED_OUT',
              }],
          })),
  )

  yield api.test(
      'expired',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data(
          'fake test (fake device iOS 8.1) (with patch)',
          api.chromium_swarming.summary(None, {
              'shards': [{
                  'state': 'EXPIRED',
              }],
          })),
  )

  yield api.test(
      'no_exit_code',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data(
          'fake test (fake device iOS 8.1) (with patch)',
          api.chromium_swarming.summary(None, {
              'shards': [{
                  'state': 'BOT_DIED',
              }],
          })),
  )

  yield api.test(
      'is_debug_missing',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version': '9abc',
          'gn_args': ['target_cpu="x86"',],
          'tests': [],
      }),
  )

  yield api.test(
      'target_cpu_missing',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version': '9abc',
          'gn_args': ['is_debug=true',],
          'tests': [],
      }),
  )

  yield api.test(
      'clobber_checkout',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.properties(clobber=True),
      api.ios.make_test_build_config({
          'xcode build version': '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [],
      }),
  )

  yield api.test(
      'clobber_build',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version': '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'clobber': True,
          'tests': [],
      }),
  )

  yield api.test(
      'fyi',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
              'priority': 199,
          },],
      }),
  )

  yield api.test(
      'expiration_test',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'bot id': 'fake99-b1',
              'device type': 'fake device',
              'os': '8.1',
              'pool': 'fake-pool',
              'expiration_time': 3600,
          },],
      }),
  )

  yield api.test(
      'max_runtime_test',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'bot id': 'fake99-b1',
              'device type': 'fake device',
              'os': '8.1',
              'pool': 'fake-pool',
              'max runtime seconds': 7200,
          },],
      }),
  )

  xcode_build_version = sum([
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9a123',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [
              {
                  'app': 'build-global xcode build version',
                  'device type': 'fake device',
                  'os': '10.0',
                  'restart': 'true',
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
      }),
  ], api.empty_test_data())

  yield api.test(
      'xcode_build_version',
      xcode_build_version,
  )

  yield api.test(
      'device_check_false',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9a123',
          'gn_args': [
              'is_debug=true',
              'target_cpu="arm64"',
          ],
          'device check':
              False,
          'tests': [{
              'app': 'build-global xcode build version',
              'device type': 'iPhone X',
              'os': '10.0',
          },],
      }),
  )

  yield api.test(
      'deprecate_xcode_version',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode version':
              '8.0',
          'gn_args': [
              'is_debug=true',
              'target_cpu="arm64"',
          ],
          'device check':
              False,
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
      }),
  )

  yield api.test(
      'use_wpr_tools',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'additional files': [
              'fake/file/path1/',
              'fake/file/path2/',
          ],
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app':
                  'fake test',
              'device type':
                  'fake device',
              'os':
                  '8.1',
              'replay package name':
                  'chromium/ios/autofill/recipe-and-replay-data',
              'replay package version':
                  'version:latest',
          },],
      }),
  )

  yield api.test(
      'xparallel_run_and_skip',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '09a123',
          'additional files': [
              'fake/file/path1/',
              'fake/file/path2/',
          ],
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'xcode parallelization': True,
              'shards': 3,
              'app': 'fake test',
              'device type': 'fake device',
              'os': '12.0.1',
          }, {
              'app': 'fake test2',
              'device type': 'fake device',
              'os': '12.0.1',
          }],
      }),
  )

  yield api.test(
      'xcodebuild_device_runner',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '11M336w',
          'additional files': [
              'fake/file/path1/',
              'fake/file/path2/',
          ],
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'xcodebuild device runner': True,
              'app': 'fake test',
              'device type': 'Real device',
              'os': '12.0.1',
          }, {
              'app': 'fake test2',
              'device type': 'Real device',
              'os': '12.0.1',
          }],
      }),
  )

  yield api.test(
      'use_trusted_cert',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
              'use trusted cert': True,
          },],
      }),
  )

  yield api.test(
      'host_app_path',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '9abc',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake test',
              'host': 'fake host app',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
  )

  yield api.test(
      'swarming_shards_for_EG2_tests',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '11M336w',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'EG2_test',
              'host': 'fake host',
              'device type': 'Real device',
              'os': '13.1.2',
              'swarming tasks': 3
          }, {
              'app': 'EG1_test2',
              'device type': 'Real device',
              'os': '13.1',
          }],
      }),
  )

  yield api.test(
      'swarming_shards_for_EG_release_app',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fyi',
          builder='ios',
          build_number=1,
          revision='HEAD',
      ),
      api.ios.make_test_build_config({
          'xcode build version':
              '11M336w',
          'gn_args': [
              'is_debug=false',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'EG2_test',
              'host': 'fake host',
              'device type': 'Real device',
              'os': '13.1.2',
              'swarming tasks': 2
          }],
      }),
  )

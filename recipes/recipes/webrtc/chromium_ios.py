# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe based on ios/unified_builder_tester adapted for using WebRTC.

The changes are:
* The Chromium checkout uses WebRTC ToT in src/third_party/WebRTC
"""

DEPS = [
    'builder_group',
    'chromium',
    'ios',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
]

def RunSteps(api):
  api.ios.checkout(gclient_apply_config=['chromium_webrtc_tot'])
  api.ios.read_build_config()
  api.ios.build()
  api.ios.test_swarming()

def GenTests(api):
  yield api.test(
      'basic_goma_build',
      api.platform('mac', 64),
      api.buildbucket.ci_build(
          builder='ios',
          git_repo='https://chromium.googlesource.com/chromium/src.git'),
      api.builder_group.for_current('chromium.fake'),
      api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'gn_args': [
              'is_debug=false',
              'target_cpu="arm"',
              'use_goma=true',
          ],
          'bucket':
              'fake-bucket-1',
          'tests': [{
              'app': 'fake test',
              'device type': 'iPhone X',
              'os': '8.0',
          },],
      }),
  )

  basic_common = sum([
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          change_number=123456,
          patch_set=7,
      ),
      api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'env': {
              'fake env var 1': 'fake env value 1',
              'fake env var 2': 'fake env value 2',
          },
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'bucket':
              'fake-bucket-1',
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
              {
                  'app': 'fake_eg_test_host',
                  'device type': 'fake device 3',
                  'os': '9.3',
                  'xctest': True,
              },
          ],
          'upload': [
              {
                  'artifact': 'fake tests 1.app',
                  'compress': True,
              },
              {
                  'artifact': 'fake tests 2.app',
                  'bucket': 'fake-bucket-2',
              },
          ],
      }),
  ], api.empty_test_data())

  yield api.test(
      'basic',
      basic_common,
  )

  yield api.test(
      'basic_experimental',
      basic_common,
      api.runtime(is_experimental=True),
  )

  yield api.test(
      'parent',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios',
          build_number=1,
          change_number=123456,
          patch_set=7,
      ),
      api.ios.make_test_build_config({
          'triggered by':
              'parent',
          'tests': [{
              'app': 'fake tests',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.ios.make_test_build_config_for_parent({
          'xcode version': 'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
      }),
  )

  yield api.test(
      'goma_compilation_failure',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='chromium.fake',
          builder='ios',
          build_number=1,
          change_number=123456,
          patch_set=7,
      ),
      api.ios.make_test_build_config({
          'xcode version':
              '6.1.1',
          'gn_args': [
              'is_debug=false',
              'target_cpu="arm"',
              'use_goma=true',
          ],
          'tests': [{
              'app': 'fake test',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data(
          'compile',
          retcode=1,
          stdout=api.raw_io.output_text('1.2.3'),
      ),
  )

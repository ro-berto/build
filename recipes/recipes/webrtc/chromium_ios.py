# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe based on ios/unified_builder_tester adapted for using WebRTC.

The changes are:
* The Chromium checkout uses WebRTC ToT in src/third_party/WebRTC
"""

DEPS = [
    'builder_group',
    'ios',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
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
      api.builder_group.for_current('chromium.fake'),
      api.properties(
          buildername='ios',
          buildnumber='0',
          bot_id='fake-vm',
      ),
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
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
  )

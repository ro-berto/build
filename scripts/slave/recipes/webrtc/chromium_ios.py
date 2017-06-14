# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe based on ios/unified_builder_tester adapted for using WebRTC.

The changes are:
* The Chromium checkout uses WebRTC ToT in src/third_party/WebRTC
* No tests are run.
"""

DEPS = [
  'ios',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
]

def RunSteps(api):
  api.ios.checkout(gclient_apply_config=['chromium_webrtc_tot'])
  api.ios.read_build_config()
  api.ios.build()

def GenTests(api):
  yield (
    api.test('basic_goma_build')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'gn_args': [
        'is_debug=false',
        'target_cpu="arm"',
        'use_goma=true',
      ],
      'tests': [
      ],
    })
  )

# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_checkout',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'ios',
  'recipe_engine/buildbucket',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'webrtc'
]


def RunSteps(api):
  api.gclient.set_config('webrtc_ios')
  api.webrtc.checkout()

  build_config_base_dir = api.path['checkout'].join(
      'tools_webrtc',
      'ios',
  )
  buildername = api.buildbucket.builder_name.replace(' ', '_')
  api.ios.read_build_config(build_config_base_dir=build_config_base_dir,
                            buildername=buildername)
  mb_path = api.path['checkout'].join('tools_webrtc', 'mb')
  api.ios.build(mb_path=mb_path)
  api.ios.test_swarming()

def GenTests(api):
  yield (
    api.test('basic')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios debug',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'gn_args': [
          'is_debug=true',
          'target_cpu="x86"',
      ],
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
        'bootstrap swarming.swarming.py --version',
         stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('no_tests')
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
    api.test('trybot')
    + api.platform('mac', 64)
    + api.properties.tryserver(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
      path_config='kitchen',
      gerrit_project='webrtc'
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'gn_args': [
        'is_debug=false',
        'target_cpu="arm"',
      ],
      'tests': [
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
         stdout=api.raw_io.output_text('1.2.3'),
    )
  )

# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'ios',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
]

def RunSteps(api):
  api.ios.checkout()
  api.ios.read_build_config()
  api.ios.build()
  if api.runtime.is_experimental:
    result = api.step('Skip upload', [])
    result.presentation.step_text = (
        'Running in experimental mode, skipping upload.')
  else:
    api.ios.upload()
  api.ios.test_swarming()

def GenTests(api):
  basic_common = (
    api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'env': {
        'fake env var 1': 'fake env value 1',
        'fake env var 2': 'fake env value 2',
      },
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'bucket': 'fake-bucket-1',
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
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('basic')
    + basic_common
    + api.runtime(is_luci=False, is_experimental=False)
  )

  yield (
    api.test('basic_experimental')
    + basic_common
    + api.runtime(is_luci=True, is_experimental=True)
  )

  yield (
    api.test('goma')
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
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('goma_canary')
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
      'use_goma_canary': True,
      'tests': [
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

  yield (
    api.test('goma_compilation_failure')
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
        'target_cpu="arm"',
        'use_goma=true',
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
        'compile',
        retcode=1,
        stdout=api.raw_io.output_text('1.2.3'),
    )
  )

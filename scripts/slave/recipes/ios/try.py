# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'ios',
  'depot_tools/gclient',
  'depot_tools/tryserver',
  'recipe_engine/buildbucket',
  'recipe_engine/json',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]

def RunSteps(api):
  with api.tryserver.set_failure_hash():
    api.ios.checkout()
    # Ensure try bots mirror configs from chromium.mac.
    api.ios.read_build_config(master_name='chromium.mac')
    api.ios.build(analyze=True, suffix='with patch')
    api.ios.test_swarming()

def GenTests(api):

  def suppress_analyze():
    """Overrides analyze step data so that all targets get compiled."""
    return api.override_step_data(
        'read filter exclusion spec',
        api.json.output({
            'base': {
                'exclusions': ['f.*'],
            },
            'chromium': {
                'exclusions': [],
            },
            'ios': {
                'exclusions': [],
            },
        })
    )

  def try_build():
    return api.buildbucket.try_build(
        project='ios',
        builder='linux',
        git_repo='https://chromium.googlesource.com/src/third_party/icu')

  yield (
    api.test('basic')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
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
          'app': 'fake tests',
          'device type': 'fake device',
          'os': '8.1',
          'xctest': True,
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + suppress_analyze()
  )

  yield (
    api.test('no_compilation')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
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
          'app': 'fake tests',
          'device type': 'fake device',
          'os': '8.1',
          'xctest': True,
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
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
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
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + suppress_analyze()
  )

  # The same test as above but applying an icu patch.
  yield (
    api.test('icu_patch')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      patch_project='icu',
      rietveld='fake://rietveld.url',
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
          'app': 'fake tests',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + suppress_analyze()
  )

  yield (
    api.test('parent')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      bot_id='fake-vm',
      path_config='kitchen',
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
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + suppress_analyze()
  )

  yield (
    api.test('gn')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator-gn',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'gn_args': [
        'is_debug=true',
        'ios_enable_code_signing=false',
        'target_cpu="x86"',
        'target_os="ios"',
        'use_goma=true',
      ],
      'use_analyze': True,
      'mb_type': 'gn',
      'tests': [
        {
          'app': 'fake tests',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + suppress_analyze()
  )

  yield (
    api.test('goma_compilation_failure')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator-gn',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'gn_args': [
        'is_debug=true',
        'ios_enable_code_signing=false',
        'target_cpu="x86"',
        'target_os="ios"',
        'use_goma=true',
      ],
      'use_analyze': True,
      'mb_type': 'gn',
      'tests': [
        {
          'app': 'fake tests',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
    + api.step_data('compile (with patch)', retcode=1)
    + suppress_analyze()
  )

  yield (
    api.test('additional_compile_targets')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'additional_compile_targets': ['fake_target'],
      'tests': [
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output_text('1.2.3'),
    )
    + suppress_analyze()
  )

  yield (
    api.test('patch_failure')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      bot_id='fake-vm',
      path_config='kitchen',
      fail_patch='apply',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'gn_args': [
        'is_debug=true',
        'target_cpu="x86"',
      ],
      'tests': [
        {
          'app': 'fake tests',
          'device type': 'fake device',
          'os': '8.1',
          'xctest': True,
        },
      ],
    })
    + api.step_data('bot_update', retcode=87)
  )

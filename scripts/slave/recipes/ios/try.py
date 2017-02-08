# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'ios',
  'depot_tools/gclient',
  'depot_tools/tryserver',
  'recipe_engine/json',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]

def RunSteps(api):
  with api.tryserver.set_failure_hash():
    bot_update_step = api.ios.checkout()
    # Ensure try bots mirror configs from chromium.mac.
    api.ios.read_build_config(master_name='chromium.mac')
    try:
      api.ios.build(analyze=True, suffix='with patch')
    except api.step.StepFailure:
      bot_update_json = bot_update_step.json.output
      api.gclient.c.revisions['src'] = str(
          bot_update_json['properties']['got_revision'])
      api.ios.checkout(patch=False, update_presentation=False)
      api.ios.build(suffix='without patch')
      raise
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

  yield (
    api.test('basic')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
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
    api.test('no_tests')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
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

  yield (
    api.test('swarming_tests_skipped')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator-swarming',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
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

  # The same test as above but applying an icu patch.
  yield (
    api.test('icu_patch')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      patch_project='icu',
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
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
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
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
    api.test('without_patch_success')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
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
    + suppress_analyze()
    + api.step_data('compile (with patch)', retcode=1)
  )

  yield (
    api.test('without_patch_failure')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
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
    + suppress_analyze()
    + api.step_data('compile (with patch)', retcode=1)
    + api.step_data('compile (without patch)', retcode=1)
  )

  yield (
    api.test('gn')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator-gn',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
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
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator-gn',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
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
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      rietveld='fake://rietveld.url',
      slavename='fake-vm',
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
  )


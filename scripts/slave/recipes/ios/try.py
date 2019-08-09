# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium_swarming',
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
  api.ios.checkout()
  # Ensure try bots mirror configs from chromium.mac.
  api.ios.read_build_config(master_name='chromium.mac')
  compile_failure = api.ios.build(analyze=True, suffix='with patch')
  if compile_failure:
    return compile_failure
  api.ios.test_swarming(retry_failed_shards=True)

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

  def try_build(git_repo=None):
    return api.buildbucket.try_build(
        project='ios',
        builder='linux',
        git_repo=git_repo or 'https://chromium.googlesource.com/chromium/src')

  yield (
    api.test('basic_success')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
    + api.step_data(
        'fake tests (fake device iOS 8.1) (with patch)',
        api.ios.generate_test_results_placeholder())
    + api.post_process(post_process.StatusSuccess)
    + api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('failure_retry_still_failure')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen'
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
    + api.step_data(
        'fake tests (fake device iOS 8.1) (with patch)',
        api.chromium_swarming.canned_summary_output(
            api.ios.generate_test_results_placeholder(failure=True),
            failure=True))
    + api.step_data(
        'fake tests (fake device iOS 8.1) (retry shards with patch)',
        api.chromium_swarming.canned_summary_output(
            api.ios.generate_test_results_placeholder(
                failure=True, swarming_number=110000),
            failure=True))
    + api.post_process(post_process.StatusFailure)
    + api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('failure_retry_success')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen'
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
    + api.step_data(
        'fake tests (fake device iOS 8.1) (with patch)',
        api.chromium_swarming.canned_summary_output(
            api.ios.generate_test_results_placeholder(failure=True),
            failure=True))
    + api.step_data(
        'fake tests (fake device iOS 8.1) (retry shards with patch)',
        api.chromium_swarming.canned_summary_output(
            api.ios.generate_test_results_placeholder(swarming_number=110000)))
    + api.post_process(post_process.StatusSuccess)
    + api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('no_compilation')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
      issue=123456,
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
    + try_build(git_repo='https://chromium.googlesource.com/chromium/deps/icu')
    + api.platform('mac', 64)
    + api.properties(
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      patch_project='icu',
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator-gn',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator-gn',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen',
      fail_patch='apply',
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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

  yield (
    api.test('mb_gen_failure')
    + try_build()
    + api.platform('mac', 64)
    + api.properties(
      issue='123456',
      mastername='tryserver.fake',
      patchset=1,
      bot_id='fake-vm',
      path_config='kitchen',
    )
    + api.buildbucket.try_build(
      project='chromium',
      builder='ios-simulator-gn',
      build_number=1,
      revision='HEAD',
      git_repo='https://chromium.googlesource.com/chromium/src',
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
    + api.step_data('generate build files (mb) (with patch)', retcode=1)
    + api.post_process(post_process.StatusFailure)
    + api.post_process(post_process.DropExpectation)
  )

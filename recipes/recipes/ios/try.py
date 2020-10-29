# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
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
  api.ios.read_build_config(builder_group='chromium.mac')
  api.ios.build(analyze=True, suffix='with patch')
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

  yield api.test(
      'basic_success',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios-simulator',
      ),
      api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake tests',
              'device type': 'fake device',
              'os': '8.1',
              'xctest': True,
          },],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
      suppress_analyze(),
      api.step_data('fake tests (fake device iOS 8.1) (with patch)',
                    api.ios.generate_test_results_placeholder()),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failure_retry_still_failure',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios-simulator',
      ),
      api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake tests',
              'device type': 'fake device',
              'os': '8.1',
              'xctest': True,
          },],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
      suppress_analyze(),
      api.step_data(
          'fake tests (fake device iOS 8.1) (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.ios.generate_test_results_placeholder(failure=True),
              failure=True)),
      api.step_data(
          'fake tests (fake device iOS 8.1) (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.ios.generate_test_results_placeholder(
                  failure=True, swarming_number=1),
              failure=True)),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failure_retry_success',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios-simulator',
      ),
      api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake tests',
              'device type': 'fake device',
              'os': '8.1',
              'xctest': True,
          },],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
      suppress_analyze(),
      api.step_data(
          'fake tests (fake device iOS 8.1) (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.ios.generate_test_results_placeholder(failure=True),
              failure=True)),
      api.step_data(
          'fake tests (fake device iOS 8.1) (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.ios.generate_test_results_placeholder(swarming_number=1))),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_compilation',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios-simulator',
          change_number=123456,
          patch_set=7,
      ),
      api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake tests',
              'device type': 'fake device',
              'os': '8.1',
              'xctest': True,
          },],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
  )

  yield api.test(
      'no_tests',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios-simulator',
          change_number=123456,
          patch_set=7,
      ),
      api.ios.make_test_build_config({
          'xcode version': 'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
      suppress_analyze(),
  )

  # The same test as above but applying an icu patch.
  yield api.test(
      'icu_patch',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios-simulator',
          build_number=1,
          change_number=123456,
          patch_set=7,
      ),
      api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake tests',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
      suppress_analyze(),
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
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
      suppress_analyze(),
  )

  yield api.test(
      'gn',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios-simulator-gn',
          build_number=1,
          change_number=123456,
          patch_set=7,
      ),
      api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'ios_enable_code_signing=false',
              'target_cpu="x86"',
              'target_os="ios"',
              'use_goma=true',
          ],
          'use_analyze':
              True,
          'mb_type':
              'gn',
          'tests': [{
              'app': 'fake tests',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
      suppress_analyze(),
  )

  yield api.test(
      'goma_compilation_failure',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios-simulator-gn',
          build_number=1,
          change_number=123456,
          patch_set=7,
      ),
      api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'ios_enable_code_signing=false',
              'target_cpu="x86"',
              'target_os="ios"',
              'use_goma=true',
          ],
          'use_analyze':
              True,
          'mb_type':
              'gn',
          'tests': [{
              'app': 'fake tests',
              'device type': 'fake device',
              'os': '8.1',
          },],
      }),
      api.step_data('compile (with patch)', retcode=1),
      suppress_analyze(),
  )

  yield api.test(
      'additional_compile_targets',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios-simulator',
          change_number=123456,
          patch_set=7,
      ),
      api.ios.make_test_build_config({
          'xcode version': 'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'additional_compile_targets': ['fake_target'],
          'tests': [],
      }),
      api.step_data(
          'bootstrap swarming.swarming.py --version',
          stdout=api.raw_io.output_text('1.2.3'),
      ),
      suppress_analyze(),
  )

  yield api.test(
      'patch_failure',
      api.platform('mac', 64),
      api.chromium.try_build(
          builder_group='tryserver.fake',
          builder='ios-simulator',
          change_number=123456,
          patch_set=7,
      ),
      api.properties(fail_patch='apply'),
      api.ios.make_test_build_config({
          'xcode version':
              'fake xcode version',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x86"',
          ],
          'tests': [{
              'app': 'fake tests',
              'device type': 'fake device',
              'os': '8.1',
              'xctest': True,
          },],
      }),
      api.step_data('bot_update', retcode=87),
  )

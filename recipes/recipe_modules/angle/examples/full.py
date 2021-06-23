# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.build.chromium_tests_builder_config import (builder_db,
                                                                builder_spec,
                                                                try_spec)

DEPS = [
    'angle',
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/path',
    'test_utils',
]


def RunSteps(api):
  return api.angle.steps()


_TEST_BUILDERS = builder_db.BuilderDatabase.create({
    'angle': {
        'android-builder':
            builder_spec.BuilderSpec.create(
                gclient_config='angle_android', chromium_config='angle_clang'),
        'linux-builder':
            builder_spec.BuilderSpec.create(
                gclient_config='angle', chromium_config='angle_clang'),
        'mac-builder':
            builder_spec.BuilderSpec.create(
                gclient_config='angle', chromium_config='angle_clang'),
        'win-builder':
            builder_spec.BuilderSpec.create(
                gclient_config='angle', chromium_config='angle_clang'),
    },
})

_TEST_TRYBOTS = try_spec.TryDatabase.create({
    'angle': {
        'android-builder':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='angle',
                        buildername='android-builder',
                    ),
                ],),
        'linux-builder':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='angle',
                        buildername='linux-builder',
                    ),
                ],),
        'mac-builder':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='angle',
                        buildername='mac-builder',
                    ),
                ],),
        'win-builder':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='angle',
                        buildername='win-builder',
                    ),
                ],),
    }
})


def GenTests(api):

  def ci_build(builder,
               toolchain='clang',
               platform='linux',
               test_mode='compile_and_test'):
    return api.angle.ci_build(
        builder=builder,
        bot_id='build1-a1',
        build_number=1234,
        toolchain=toolchain,
        platform=platform,
        test_mode=test_mode,
    ) + api.angle.builders(_TEST_BUILDERS) + api.angle.trybots(_TEST_TRYBOTS)

  yield api.test(
      'android_test',
      ci_build('android-builder', platform='android', test_mode='compile_only'),
  )
  yield api.test(
      'basic_test',
      ci_build('linux-builder'),
  )
  yield api.test(
      'basic_mac_test',
      api.platform('mac', 64),
      ci_build('mac-builder', platform='mac', test_mode='compile_only'),
  )
  yield api.test(
      'compile_only_compile_failed_test',
      ci_build('linux-builder', test_mode='compile_only'),
      api.step_data('compile', api.legacy_annotation.infra_failure_step),
  )
  yield api.test(
      'compile_and_test_compile_failed_test',
      ci_build('linux-builder'),
      api.step_data('compile', api.legacy_annotation.infra_failure_step),
  )
  yield api.test(
      'win_non_clang_test',
      api.platform('win', 64),
      ci_build(
          builder='win-builder',
          toolchain='msvc',
          platform='win',
          test_mode='compile_only'),
  )
  yield api.test(
      'linux_non_clang_test',
      api.platform('linux', 64),
      ci_build(
          builder='linux-builder', toolchain='gcc', test_mode='checkout_only'),
  )
  yield api.test(
      'linux_trace_test',
      api.platform('linux', 64),
      ci_build(builder='linux-builder', test_mode='trace_tests'),
  )
  yield api.test(
      'win_trace_test',
      api.platform('win', 64),
      ci_build(builder='win-builder', platform='win', test_mode='trace_tests'),
  )
  yield api.test(
      'win_trace_test_failure',
      api.platform('win', 64),
      ci_build(builder='win-builder', platform='win', test_mode='trace_tests'),
      api.step_data('GLES 2.0 trace tests',
                    api.legacy_annotation.infra_failure_step),
  )
  yield api.test(
      'invalid_json_test',
      ci_build('linux-builder'),
      api.chromium_tests.read_source_side_spec(
          'angle', {
              'linux-builder': {
                  'isolated_scripts': [{
                      'isolate_name': 'basic_isolate',
                      'name': 'basic_isolate_tests',
                  },],
              },
          }),
      api.override_step_data(
          'basic_isolate_tests',
          api.chromium_swarming.canned_summary_output(
              api.json.output({'version': 2}))),
  )
  yield api.test(
      'failed_json_test',
      ci_build('linux-builder'),
      api.chromium_tests.read_source_side_spec(
          'angle', {
              'linux-builder': {
                  'isolated_scripts': [{
                      'isolate_name': 'basic_isolate',
                      'name': 'basic_isolate_tests',
                  },],
              },
          }),
      api.override_step_data(
          'basic_isolate_tests',
          api.test_utils.canned_isolated_script_output(
              passing=False,
              is_win=False,
              swarming=False,
              isolated_script_passing=False,
              use_json_test_format=True),
          retcode=0),
  )

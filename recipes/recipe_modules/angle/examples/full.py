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
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/legacy_annotation',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/path',
]


def RunSteps(api):
  return api.angle.steps()


_TEST_BUILDERS = builder_db.BuilderDatabase.create({
    'angle': {
        'android-builder':
            builder_spec.BuilderSpec.create(chromium_config='angle'),
        'linux-builder':
            builder_spec.BuilderSpec.create(chromium_config='angle'),
        'mac-builder':
            builder_spec.BuilderSpec.create(chromium_config='angle'),
        'win-builder':
            builder_spec.BuilderSpec.create(chromium_config='angle'),
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

  def ci_build(builder):
    return api.chromium.ci_build(
        builder_group='angle',
        builder=builder,
        bot_id='build1-a1',
        build_number=1234,
        git_repo='https://chromium.googlesource.com/angle/angle.git'
    ) + api.angle.builders(_TEST_BUILDERS) + api.angle.trybots(_TEST_TRYBOTS)

  yield api.test('android_test', ci_build('android-builder'),
                 api.properties(platform='android'),
                 api.properties(test_mode='compile_only'))
  yield api.test('basic_test', ci_build('linux-builder'),
                 api.properties(test_mode='compile_and_test'))
  yield api.test('basic_mac_test', api.platform('mac', 64),
                 ci_build('mac-builder'),
                 api.properties(test_mode='compile_only'))
  yield api.test(
      'compile_only_compile_failed_test',
      api.properties(test_mode='compile_only'), ci_build('linux-builder'),
      api.step_data('compile', api.legacy_annotation.infra_failure_step))
  yield api.test(
      'compile_and_test_compile_failed_test',
      api.properties(test_mode='compile_and_test'), ci_build('linux-builder'),
      api.step_data('compile', api.legacy_annotation.infra_failure_step))
  yield api.test(
      'win_non_clang_test', api.platform('win', 64),
      api.properties(
          toolchain='msvc', platform='win', test_mode='compile_only'),
      ci_build(builder='win-builder'))
  yield api.test('linux_non_clang_test', api.platform('linux', 64),
                 api.properties(toolchain='gcc', test_mode='checkout_only'),
                 ci_build(builder='linux-builder'))
  yield api.test('linux_trace_test', api.platform('linux', 64),
                 api.properties(test_mode='trace_tests'),
                 ci_build(builder='linux-builder'))
  yield api.test('win_trace_test', api.platform('win', 64),
                 api.properties(test_mode='trace_tests'),
                 ci_build(builder='win-builder'))

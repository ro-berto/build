# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

DEPS = [
    'angle',
    'chromium',
    'recipe_engine/buildbucket',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/path',
]


def RunSteps(api):
  api.angle.steps()


def GenTests(api):

  def ci_build(builder):
    return api.chromium.ci_build(
        builder_group='angle',
        builder=builder,
        bot_id='build1-a1',
        build_number=1234,
        git_repo='https://chromium.googlesource.com/angle/angle.git')

  yield api.test('android_test', ci_build('ANGLE Test Android Builder'),
                 api.properties(platform='android'))
  yield api.test('basic_test', ci_build('ANGLE Test Builder'))
  yield api.test('basic_mac_test', api.platform('mac', 64),
                 ci_build('ANGLE Test Mac Builder'))
  yield api.test('win_non_clang_test', api.platform('win', 64),
                 api.properties(toolchain='msvc'),
                 ci_build(builder='ANGLE Test Win Non-Clang Builder'))
  yield api.test('linux_non_clang_test', api.platform('linux', 64),
                 api.properties(toolchain='gcc', test_mode='checkout_only'),
                 ci_build(builder='ANGLE Test Linux Non-Clang Builder'))
  yield api.test('linux_trace_test', api.platform('linux', 64),
                 api.properties(test_mode='trace_tests'),
                 ci_build(builder='ANGLE Test Trace Linux Builder'))
  yield api.test('win_trace_test', api.platform('win', 64),
                 api.properties(test_mode='trace_tests'),
                 ci_build(builder='ANGLE Test Trace Win Builder'))

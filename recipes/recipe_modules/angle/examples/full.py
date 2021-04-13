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

PROPERTIES = {
    'clang': Property(default=True, kind=bool),
    'trace_tests': Property(default=False, kind=bool),
}


def RunSteps(api, clang, trace_tests):
  angle = api.angle
  angle.apply_bot_config(clang)

  if trace_tests:
    angle.trace_tests(clang)
  else:
    angle.compile(clang)


def GenTests(api):

  def ci_build(builder):
    return api.chromium.ci_build(
        builder_group='angle',
        builder=builder,
        bot_id='build1-a1',
        build_number=1234,
        git_repo='https://chromium.googlesource.com/angle/angle.git')

  yield api.test('basic_test', ci_build('ANGLE Test Builder'))
  yield api.test('basic_mac_test', api.platform('mac', 64),
                 ci_build('ANGLE Test Mac Builder'))
  yield api.test('win_non_clang_test', api.platform('win', 64),
                 api.properties(clang=False),
                 ci_build(builder='ANGLE Test Win Non-Clang Builder'))
  yield api.test('linux_non_clang_test', api.platform('linux', 64),
                 api.properties(clang=False),
                 ci_build(builder='ANGLE Test Linux Non-Clang Builder'))
  yield api.test('linux_trace_test', api.platform('linux', 64),
                 api.properties(trace_tests=True),
                 ci_build(builder='ANGLE Test Trace Linux Builder'))
  yield api.test('win_trace_test', api.platform('win', 64),
                 api.properties(trace_tests=True),
                 ci_build(builder='ANGLE Test Trace Win Builder'))

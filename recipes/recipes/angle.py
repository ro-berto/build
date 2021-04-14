# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'angle',
    'builder_group',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/gsutil',
    'goma',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'recipe_engine/time',
]

from recipe_engine.recipe_api import Property

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
    return angle.compile(clang)


def GenTests(api):

  def ci_build(builder):
    return api.buildbucket.ci_build(
        project='angle',
        builder=builder,
        build_number=1234,
        git_repo='https://chromium.googlesource.com/angle/angle.git')

  yield api.test(
      'linux',
      api.platform('linux', 64),
      ci_build(builder='linux'),
      api.builder_group.for_current('client.angle'),
  )
  yield api.test(
      'linux_gcc',
      api.platform('linux', 64),
      ci_build(builder='linux-gcc'),
      api.builder_group.for_current('client.angle'),
      api.properties(clang=False),
  )
  yield api.test(
      'linux_trace',
      api.platform('linux', 64),
      ci_build(builder='linux'),
      api.builder_group.for_current('client.angle'),
      api.properties(clang=True, trace_tests=True),
  )
  yield api.test(
      'win',
      api.platform('win', 64),
      ci_build(builder='windows'),
      api.builder_group.for_current('client.angle'),
  )
  yield api.test(
      'win_clang',
      api.platform('win', 64),
      ci_build(builder='windows'),
      api.builder_group.for_current('client.angle'),
      api.properties(clang=True),
  )
  yield api.test(
      'win_rel_msvc_x86',
      api.platform('win', 64),
      ci_build(builder='windows'),
      api.builder_group.for_current('client.angle'),
      api.properties(clang=False, debug=False, target_cpu='x86'),
  )
  yield api.test(
      'winuwp_dbg_msvc_x64',
      api.platform('win', 64),
      ci_build(builder='windows'),
      api.builder_group.for_current('client.angle'),
      api.properties(clang=False, debug=True, uwp=True),
  )
  yield api.test(
      'win_trace',
      api.platform('win', 64),
      ci_build(builder='windows'),
      api.builder_group.for_current('client.angle'),
      api.properties(clang=True, trace_tests=True),
  )

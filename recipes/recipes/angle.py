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


def RunSteps(api):
  return api.angle.steps()


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

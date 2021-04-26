# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, try_spec

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


_TEST_BUILDERS = bot_db.BotDatabase.create({
    'angle': {
        'linux-builder': bot_spec.BotSpec.create(chromium_config='angle'),
    },
})

_TEST_TRYBOTS = try_spec.TryDatabase.create({
    'angle': {
        'linux-builder':
            try_spec.TrySpec.create(
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='angle',
                        buildername='linux-builder',
                    ),
                ],),
    }
})


def GenTests(api):

  yield api.test(
      'linux', api.platform('linux', 64),
      api.buildbucket.ci_build(
          project='angle',
          builder='linux-builder',
          build_number=1234,
          git_repo='https://chromium.googlesource.com/angle/angle.git'),
      api.angle.builders(_TEST_BUILDERS), api.angle.trybots(_TEST_TRYBOTS),
      api.properties(test_mode='compile_and_test'),
      api.builder_group.for_current('angle'))

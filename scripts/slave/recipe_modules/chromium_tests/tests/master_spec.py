# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_spec, master_spec

DEPS = [
    'recipe_engine/assertions',
]


def RunSteps(api):
  # normalize ******************************************************************
  x = master_spec.MasterSpec.normalize({
      'builders': {
          'fake-builder': {
              'bot_type': bot_spec.BUILDER,
          },
      },
  })
  y = master_spec.MasterSpec.create(
      builders={
          'fake-builder': bot_spec.BotSpec.create(bot_type=bot_spec.BUILDER),
      },
  )
  api.assertions.assertEqual(x, y)

  z = master_spec.MasterSpec.normalize(y)
  api.assertions.assertIs(y, z)


def GenTests(api):
  yield api.test(
      'full',
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

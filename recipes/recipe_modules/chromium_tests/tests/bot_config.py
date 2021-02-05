# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import bot_config as bot_config_module
from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, try_spec

DEPS = [
    'recipe_engine/assertions',
]


def RunSteps(api):
  # Set up data for testing bot_config methods
  builders = bot_db.BotDatabase.create({
      'fake-group': {
          'fake-builder':
              bot_spec.BotSpec.create(),
          'fake-tester':
              bot_spec.BotSpec.create(
                  execution_mode=bot_spec.TEST,
                  parent_buildername='fake-builder',
              ),
      },
      'fake-group2': {
          'fake-builder2':
              bot_spec.BotSpec.create(),
          'fake-tester2':
              bot_spec.BotSpec.create(
                  execution_mode=bot_spec.TEST,
                  parent_buildername='fake-builder',
              ),
      },
  })

  # Test builders_id method
  bot_config = bot_config_module.BotConfig.create(builders, [
      try_spec.TryMirror.create(
          builder_group='fake-group',
          buildername='fake-builder',
          tester='fake-tester'),
      try_spec.TryMirror.create(
          builder_group='fake-group2',
          buildername='fake-builder2',
          tester='fake-tester2'),
  ])
  api.assertions.assertEqual(bot_config.builder_ids, (
      chromium.BuilderId.create_for_group('fake-group', 'fake-builder'),
      chromium.BuilderId.create_for_group('fake-group2', 'fake-builder2'),
  ))


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

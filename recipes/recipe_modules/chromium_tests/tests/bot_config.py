# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import bot_config as bot_config_module
from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, try_spec

DEPS = [
    'recipe_engine/assertions',
    'recipe_engine/python',
    'recipe_engine/step',
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

  # Test create failures
  with api.assertions.assertRaises(
      bot_config_module.BotConfigException) as caught:
    bot_config_module.BotConfig.create(
        builders,
        try_spec.TrySpec.create_for_single_mirror(
            builder_group='non-existent-group', buildername='fake-builder'))
  message = "No configuration present for group 'non-existent-group'"
  api.assertions.assertEqual(str(caught.exception), message)

  with api.assertions.assertRaises(
      bot_config_module.BotConfigException) as caught:
    bot_config_module.BotConfig.create(
        builders,
        try_spec.TrySpec.create_for_single_mirror(
            builder_group='fake-group', buildername='non-existent-builder'))
  message = ("No configuration present for builder 'non-existent-builder'"
             " in group 'fake-group'")
  api.assertions.assertEqual(str(caught.exception), message)

  # Test create failure when using python API
  with api.assertions.assertRaises(api.step.InfraFailure) as caught:
    bot_config_module.BotConfig.create(
        builders,
        try_spec.TrySpec.create_for_single_mirror(
            builder_group='non-existent-group', buildername='fake-builder'),
        python_api=api.python)
  name = "No configuration present for group 'non-existent-group'"
  api.assertions.assertEqual(caught.exception.result.name, name)

  # Test builders_id method
  bot_config = bot_config_module.BotConfig.create(
      builders,
      try_spec.TrySpec.create([
          try_spec.TryMirror.create(
              builder_group='fake-group',
              buildername='fake-builder',
              tester='fake-tester'),
          try_spec.TryMirror.create(
              builder_group='fake-group2',
              buildername='fake-builder2',
              tester='fake-tester2'),
      ]))
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

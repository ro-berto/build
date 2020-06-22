# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import bot_config as bot_config_module
from RECIPE_MODULES.build.chromium_tests import bot_spec

DEPS = [
    'recipe_engine/assertions',
]


def RunSteps(api):
  # Test failed normalization of bot specs
  spec = {'execution_mode': bot_spec.TEST}
  builders = {
      'fake-master': {
              'fake-builder': spec,
      },
  }
  builder_id = chromium.BuilderId.create_for_master('fake-master',
                                                    'fake-builder')
  with api.assertions.assertRaises(AssertionError) as caught:
    bot_config_module.BotConfig.create(builders, [builder_id])
  message = ('Test-only builder must specify a parent builder '
             "while creating spec for builder {!r}".format(builder_id))
  api.assertions.assertEqual(message, caught.exception.message)

  # Set up data for testing bot_config methods
  builders = {
      'fake-master': {
          'fake-builder':
              bot_spec.BotSpec.create(),
          'fake-tester':
              bot_spec.BotSpec.create(
                  execution_mode=bot_spec.TEST,
                  parent_buildername='fake-builder',
              ),
      },
      'fake-master2': {
          'fake-builder2':
              bot_spec.BotSpec.create(),
          'fake-tester2':
              bot_spec.BotSpec.create(
                  execution_mode=bot_spec.TEST,
                  parent_buildername='fake-builder',
              ),
      },
  }

  # Test builders_id method
  bot_config = bot_config_module.BotConfig.create(builders, [
      {
          'mastername': 'fake-master',
          'buildername': 'fake-builder',
          'tester': 'fake-tester'
      },
      {
          'mastername': 'fake-master2',
          'buildername': 'fake-builder2',
          'tester': 'fake-tester2'
      },
  ])
  api.assertions.assertEqual(bot_config.builder_ids, (
      chromium.BuilderId.create_for_master('fake-master', 'fake-builder'),
      chromium.BuilderId.create_for_master('fake-master2', 'fake-builder2'),
  ))


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

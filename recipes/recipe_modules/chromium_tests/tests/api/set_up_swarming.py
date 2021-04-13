# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_swarming',
    'chromium_tests',
    'isolate',
    'recipe_engine/assertions',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium.types import BuilderId
from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec


def RunSteps(api):
  _, bot_config = api.chromium_tests.lookup_builder(
      BuilderId.create_for_group('test_group', 'test_buildername'),
      bot_db=bot_db.BotDatabase.create({
          'test_group': {
              'test_buildername':
                  bot_spec.BotSpec.create(
                      isolate_server='https://example/isolate',
                      swarming_server='https://example/swarming',
                      swarming_dimensions={'os': 'Ubuntu-14.04'},
                  ),
          },
      }))

  api.chromium_tests.set_up_swarming(bot_config)
  api.assertions.assertEqual(api.chromium_swarming.swarming_server,
                             api.properties.get('expected_swarming_server'))
  api.assertions.assertEqual(api.chromium_swarming.default_dimensions,
                             api.properties.get('expected_swarming_dimensions'))
  api.assertions.assertEqual(api.isolate.isolate_server,
                             api.properties.get('expected_isolate_server'))


def GenTests(api):
  yield api.test(
      'luci',
      api.platform.name('linux'),
      api.properties(
          expected_swarming_server='https://example/swarming',
          expected_swarming_dimensions={
              'cpu': 'x86-64',
              'gpu': None,
              'os': 'Ubuntu-14.04',
          },
          expected_isolate_server='https://example/isolate',
          expected_isolate_service_account=None),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

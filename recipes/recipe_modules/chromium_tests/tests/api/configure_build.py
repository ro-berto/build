# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec

DEPS = [
    'chromium',
    'chromium_tests',
]

BUILDERS = bot_db.BotDatabase.create({
    'fake.group': {
        'Android Apply Config Builder':
            bot_spec.BotSpec.create(
                android_config='main_builder_mb',
                chromium_config='chromium',
                gclient_config='chromium',
                test_results_config='public_server',
                android_apply_config=['use_devil_provision'],
            ),
    },
})


def RunSteps(api):
  bot_config_object = api.chromium_tests.create_bot_config_object(
      [api.chromium.get_builder_id()], builders=BUILDERS)
  api.chromium_tests.configure_build(bot_config_object)


def GenTests(api):
  yield api.test(
      'android_apply_config',
      api.chromium.ci_build(
          builder_group='fake.group', builder='Android Apply Config Builder'),
      api.post_process(post_process.DropExpectation),
  )

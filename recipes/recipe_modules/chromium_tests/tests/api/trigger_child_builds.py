# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from PB.recipe_modules.recipe_engine.led import properties as led_properties_pb

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  bot = api.chromium_tests.lookup_bot_metadata()
  api.chromium_tests.configure_build(bot.settings)
  update_step, _ = api.chromium_tests.prepare_checkout(bot.settings)
  api.chromium_tests.trigger_child_builds(builder_id, update_step, bot.settings)


def GenTests(api):

  def builder_with_tester_to_trigger():
    return sum([
        api.chromium.ci_build(
            builder_group='fake-group', builder='fake-builder'),
        api.chromium_tests.builders(
            bot_db.BotDatabase.create({
                'fake-group': {
                    'fake-builder':
                        bot_spec.BotSpec.create(
                            chromium_config='chromium',
                            gclient_config='chromium',
                        ),
                    'fake-tester':
                        bot_spec.BotSpec.create(
                            execution_mode=bot_spec.TEST,
                            chromium_config='chromium',
                            gclient_config='chromium',
                            parent_buildername='fake-builder',
                        )
                }
            }))
    ], api.empty_test_data())

  yield api.test(
      'scheduler',
      builder_with_tester_to_trigger(),
      api.post_check(post_process.StatusSuccess),
  )

  led_properties = led_properties_pb.InputProperties()
  led_properties.led_run_id = 'fake-id'
  yield api.test(
      'led',
      builder_with_tester_to_trigger(),
      api.properties(
          **{
              '$recipe_engine/led': {
                  'led_run_id': 'fake-run-id',
                  'isolated_input': {
                      'hash': 'fake-hash',
                  },
              },
          }),
      api.post_check(post_process.StatusSuccess),
  )

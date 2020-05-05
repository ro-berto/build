# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/properties',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec

DUMMY_BUILDERS = bot_db.BotDatabase.create({
    'chromium.fake': {
        'cross-master-trigger-builder':
            bot_spec.BotSpec.create(
                bot_type='builder',
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                },
                gclient_config='chromium',
            ),
    },
    'chromium.fake.fyi': {
        'cross-master-trigger-tester':
            bot_spec.BotSpec.create(
                bot_type='tester',
                parent_buildername='cross-master-trigger-builder',
                parent_mastername='chromium.fake',
            ),
    },
})


def RunSteps(api):
  bot = api.chromium_tests.lookup_bot_metadata()
  api.chromium_tests.configure_build(bot.settings)
  api.chromium_tests.prepare_checkout(bot.settings)


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          mastername='chromium.linux', builder='Linux Builder'),
  )

  yield api.test(
      'disable_tests',
      api.chromium.ci_build(mastername='fake-master', builder='fake-builder'),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'fake-master': {
                  'fake-builder':
                      bot_spec.BotSpec.create(
                          gclient_config='chromium',
                          disable_tests=True,
                      ),
              },
          })),
  )

  yield api.test(
      'cross_master_trigger',
      api.chromium.ci_build(
          mastername='chromium.fake', builder='cross-master-trigger-builder'),
      api.chromium_tests.builders(DUMMY_BUILDERS),
      api.post_process(post_process.MustRun,
                       'read test spec (chromium.fake.fyi.json)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mirror-with-non-child-tester',
      api.chromium.try_build(
          mastername='fake-try-master',
          builder='fake-try-builder',
      ),
      api.chromium_tests.builders({
          'fake-master': {
              'fake-builder': {
                  'chromium_config': 'chromium',
                  'gclient_config': 'chromium',
              },
          },
          'fake-tester-master': {
              'fake-tester': {
                  'bot_type': bot_spec.DUMMY_TESTER,
              },
          },
      }),
      api.chromium_tests.trybots({
          'fake-try-master': {
              'fake-try-builder': {
                  'bot_ids': [{
                      'mastername': 'fake-master',
                      'buildername': 'fake-builder',
                      'tester_mastername': 'fake-tester-master',
                      'tester': 'fake-tester',
                  }],
              },
          },
      }),
      api.post_process(post_process.MustRun,
                       'read test spec (fake-tester-master.json)'),
      api.post_process(post_process.DropExpectation),
  )

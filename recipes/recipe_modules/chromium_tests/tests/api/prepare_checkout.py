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

from PB.recipe_modules.build.chromium_tests.properties import InputProperties

DUMMY_BUILDERS = bot_db.BotDatabase.create({
    'chromium.fake': {
        'cross-group-trigger-builder':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                },
                gclient_config='chromium',
            ),
    },
    'chromium.fake.fyi': {
        'cross-group-trigger-tester':
            bot_spec.BotSpec.create(
                execution_mode=bot_spec.TEST,
                parent_buildername='cross-group-trigger-builder',
                parent_builder_group='chromium.fake',
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
          builder_group='chromium.linux', builder='Linux Builder'),
  )

  yield api.test(
      'cross_group_trigger',
      api.chromium.ci_build(
          builder_group='chromium.fake', builder='cross-group-trigger-builder'),
      api.chromium_tests.builders(DUMMY_BUILDERS),
      api.post_process(post_process.MustRun,
                       'read test spec (chromium.fake.fyi.json)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'trigger-with-fixed-revisions',
      api.chromium.ci_build(builder_group='fake-group', builder='fake-tester'),
      api.chromium_tests.builders({
          'fake-group': {
              'fake-tester': {
                  'chromium_config': 'chromium',
                  'gclient_config': 'chromium',
              },
          },
      }),
      api.properties(
          **{
              '$build/chromium_tests':
                  InputProperties(fixed_revisions={
                      'src': 'fake-src-revision',
                      'src/foo': 'fake-foo-revision',
                  }),
          }),
      api.post_check(post_process.StepCommandContains, 'bot_update',
                     ['--revision', 'src@fake-src-revision']),
      api.post_check(post_process.StepCommandContains, 'bot_update',
                     ['--revision', 'src/foo@fake-foo-revision']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mirror-with-non-child-tester',
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      api.chromium_tests.builders({
          'fake-group': {
              'fake-builder': {
                  'chromium_config': 'chromium',
                  'gclient_config': 'chromium',
              },
          },
          'fake-tester-group': {
              'fake-tester': {
                  'execution_mode': bot_spec.PROVIDE_TEST_SPEC,
              },
          },
      }),
      api.chromium_tests.trybots({
          'fake-try-group': {
              'fake-try-builder': {
                  'mirrors': [{
                      'builder_group': 'fake-group',
                      'buildername': 'fake-builder',
                      'tester_group': 'fake-tester-group',
                      'tester': 'fake-tester',
                  }],
              },
          },
      }),
      api.post_process(post_process.MustRun,
                       'read test spec (fake-tester-group.json)'),
      api.post_process(post_process.DropExpectation),
  )

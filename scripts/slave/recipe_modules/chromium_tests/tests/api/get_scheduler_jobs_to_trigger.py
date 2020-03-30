# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, master_spec

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/assertions',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  bot_config = api.chromium_tests.create_bot_config_object([builder_id])
  api.chromium_tests.configure_build(bot_config)
  actual = api.chromium_tests._get_scheduler_jobs_to_trigger(
      builder_id, bot_config)

  # Convert the mappings to comparable types
  actual = {k: set(v) for k, v in actual.iteritems()}
  expected = {k: set(v) for k, v in api.properties['expected'].iteritems()}

  api.assertions.assertEqual(actual, expected)


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          mastername='chromium.linux',
          builder='Linux Builder',
      ),
      api.properties(expected={
          'chromium': ['Linux Tests'],
      },),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'bucketed-triggers',
      api.chromium.ci_build(
          mastername='chromium.linux',
          builder='Linux Builder',
      ),
      api.properties(
          expected={
              'chromium': ['ci-Linux Tests'],
          },
          **{
              '$build/chromium_tests': {
                  'bucketed_triggers': True,
              },
          }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'luci-project-overridden-for-tester',
      api.chromium.ci_build(
          mastername='fake-master',
          builder='fake-builder',
      ),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'fake-master':
                  master_spec.MasterSpec.create(
                      builders={
                          'fake-builder':
                              bot_spec.BotSpec.create(),
                          'fake-tester':
                              bot_spec.BotSpec.create(
                                  luci_project='fake-project',
                                  bot_type=bot_spec.TESTER,
                                  parent_buildername='fake-builder',
                              ),
                      },
                  ),
          })),
      api.properties(expected={
          'fake-project': ['fake-tester'],
      }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

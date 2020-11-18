# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/json',
    'recipe_engine/properties',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, steps

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

  yield api.test(
      'bad-spec',
      api.chromium.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
      ),
      api.chromium_tests.builders({
          'fake-group': {
              'fake-builder': {
                  'chromium_config': 'chromium',
                  'gclient_config': 'chromium',
              },
          },
      }),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': 'invalid-spec',
      }),
      api.expect_exception('AttributeError'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'bad-spec-on-related-builder',
      api.chromium.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
      ),
      api.chromium_tests.builders({
          'fake-group': {
              'fake-builder': {
                  'chromium_config': 'chromium',
                  'gclient_config': 'chromium',
              },
              'fake-builder-with-bad-spec': {
                  'execution_mode': bot_spec.TEST,
                  'chromium_config': 'chromium',
                  'gclient_config': 'chromium',
                  'parent_buildername': 'fake-builder',
              },
          },
      }),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {},
          'fake-builder-with-bad-spec': 'invalid-spec',
      }),
      api.expect_exception('AttributeError'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'bad-spec-on-unrelated-builder',
      api.chromium.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
      ),
      api.chromium_tests.builders({
          'fake-group': {
              'fake-builder': {
                  'chromium_config': 'chromium',
                  'gclient_config': 'chromium',
              },
              'fake-builder-with-bad-spec': {
                  'chromium_config': 'chromium',
                  'gclient_config': 'chromium',
              },
          },
      }),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {},
          'fake-builder-with-bad-spec': 'invalid-spec',
      }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  group = 'fake-group'
  builder = 'fake-builder'

  def fake_builder(test_specs, builder_source_side_spec=None):
    data = api.chromium.ci_build(builder_group=group, builder=builder)
    data += api.chromium_tests.builders(
        bot_db.BotDatabase.create({
            group: {
                builder:
                    bot_spec.BotSpec.create(
                        chromium_config='chromium',
                        gclient_config='chromium',
                        test_specs=test_specs,
                    ),
            },
        }))
    if builder_source_side_spec:
      data += api.chromium_tests.read_source_side_spec(
          builder_group=group,
          contents={
              builder: builder_source_side_spec,
          },
      )
    return data

  def migration_step(migration_type, test):
    return 'test spec migration.{}.{}.{}.{}'.format(migration_type, group,
                                                    builder, test)

  yield api.test(
      'test-migration-needs-migration',
      fake_builder(test_specs=[
          bot_spec.TestSpec.create(steps.LocalIsolatedScriptTest, 'fake-test'),
      ]),
      api.post_check(post_process.MustRun,
                     migration_step('needs migration', 'fake-test')),
      api.post_process(post_process.DropExpectation),
  )

  # Test cases for already migrated tests: 1 for each type of test that can be
  # produced via ALL_GENERATORS, specifying the minimum set of arguments to
  # ensure that default argument handling works for each type
  def already_migrated_test(name, test_spec, builder_source_side_spec):
    return api.test(
        name,
        fake_builder(
            test_specs=[test_spec],
            builder_source_side_spec=builder_source_side_spec),
        api.post_check(post_process.MustRun,
                       migration_step('already migrated', 'fake-test')),
        api.post_process(post_process.DropExpectation),
    )

  yield already_migrated_test(
      'test-migration-already-migrated-isolated-scripts',
      test_spec=bot_spec.TestSpec.create(steps.LocalIsolatedScriptTest,
                                         'fake-test'),
      builder_source_side_spec={
          'isolated_scripts': [{
              'name': 'fake-test',
          }],
      },
  )

  yield already_migrated_test(
      'test-migration-already-migrated-isolated-scripts-swarming',
      test_spec=bot_spec.TestSpec.create(steps.SwarmingIsolatedScriptTest,
                                         'fake-test'),
      builder_source_side_spec={
          'isolated_scripts': [{
              'name': 'fake-test',
              'swarming': {
                  'can_use_on_swarming_builders': True
              },
          }],
      },
  )

  yield already_migrated_test(
      'test-migration-already-migrated-gtest-tests',
      test_spec=bot_spec.TestSpec.create(steps.LocalGTestTest, 'fake-test'),
      builder_source_side_spec={
          'gtest_tests': [{
              'test': 'fake-test',
          }],
      })

  yield already_migrated_test(
      'test-migration-already-migrated-gtest-tests-swarming',
      test_spec=bot_spec.TestSpec.create(steps.SwarmingGTestTest, 'fake-test'),
      builder_source_side_spec={
          'gtest_tests': [{
              'test': 'fake-test',
              'swarming': {
                  'can_use_on_swarming_builders': True
              },
          }],
      })

  yield already_migrated_test(
      'test-migration-already-migrated-junit-tests',
      test_spec=bot_spec.TestSpec.create(
          steps.ScriptTest,
          'fake-test',
          script='fake-script',
          all_compile_targets={}),
      builder_source_side_spec={
          'scripts': [{
              'name': 'fake-test',
              'script': 'fake-script',
          }],
      },
  )

  yield already_migrated_test(
      'test-migration-already-migrated-scripts',
      test_spec=bot_spec.TestSpec.create(
          steps.AndroidJunitTest, 'fake-test', target_name='fake-target'),
      builder_source_side_spec={
          'junit_tests': [{
              'name': 'fake-test',
              'test': 'fake-target',
          }],
      },
  )

  yield api.test(
      'test-migration-mismatch',
      fake_builder(
          test_specs=[
              bot_spec.TestSpec.create(
                  steps.ScriptTest,
                  'fake-test',
                  script='fake-script',
                  all_compile_targets={}),
          ],
          builder_source_side_spec={
              'scripts': [{
                  'name': 'fake-test',
                  'script': 'fake-script2',
              }],
          },
      ),
  )

  yield api.test(
      'test-migration-mismatch-experimental',
      fake_builder(
          test_specs=[
              bot_spec.TestSpec.create(steps.LocalIsolatedScriptTest,
                                       'fake-test'),
          ],
          builder_source_side_spec={
              'isolated_scripts': [{
                  'name': 'fake-test',
                  'experiment_percentage': 10,
              }],
          },
      ),
  )

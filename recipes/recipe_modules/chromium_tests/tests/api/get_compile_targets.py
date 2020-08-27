# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec


def RunSteps(api):
  bot = api.chromium_tests.lookup_bot_metadata()
  api.chromium_tests.configure_build(bot.settings)
  _, build_config = api.chromium_tests.prepare_checkout(bot.settings)
  build_config.get_compile_targets([])


def GenTests(api):

  def spec(compile_targets=()):
    return bot_spec.BotSpec.create(
        chromium_config='chromium',
        gclient_config='chromium',
        compile_targets=compile_targets,
    )

  yield api.test(
      'not-migrated',
      api.chromium.ci_build(builder_group='fake-group', builder='fake-builder'),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'fake-group': {
                  'fake-builder':
                      spec(compile_targets=['foo', 'bar', 'baz', 'shaz']),
              },
          })),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {},
      }),
      api.post_check(
          post_process.DoesNotRunRE, 'compile_targets migration\.migrated\.'
          'fake-group%fake-builder%.*'),
      api.post_check(
          post_process.MustRun, 'compile_targets migration.needs migration.'
          'fake-group%fake-builder%bar,baz,foo,shaz'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'partially-migrated',
      api.chromium.ci_build(builder_group='fake-group', builder='fake-builder'),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'fake-group': {
                  'fake-builder':
                      spec(compile_targets=['foo', 'bar', 'baz', 'shaz']),
              },
          })),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {
              'additional_compile_targets': ['foo', 'baz'],
          },
      }),
      api.post_check(
          post_process.MustRun, 'compile_targets migration.migrated.'
          'fake-group%fake-builder%baz,foo'),
      api.post_check(
          post_process.MustRun, 'compile_targets migration.needs migration.'
          'fake-group%fake-builder%bar,shaz'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'fully-migrated',
      api.chromium.ci_build(builder_group='fake-group', builder='fake-builder'),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'fake-group': {
                  'fake-builder':
                      spec(compile_targets=['foo', 'bar', 'baz', 'shaz']),
              },
          })),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'additional_compile_targets': ['foo', 'bar', 'baz', 'shaz'],
              },
          }),
      api.post_check(
          post_process.MustRun, 'compile_targets migration.migrated.'
          'fake-group%fake-builder%bar,baz,foo,shaz'),
      api.post_check(
          post_process.DoesNotRunRE,
          'compile_targets migration\.needs migration\.'
          'fake-group%fake-builder%.*'),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

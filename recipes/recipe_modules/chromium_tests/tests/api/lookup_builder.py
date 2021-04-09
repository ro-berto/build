# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, try_spec

DEPS = [
    'chromium',
    'chromium_tests',
]

BOT_DB = bot_db.BotDatabase.create({
    'fake-group': {
        'fake-builder': bot_spec.BotSpec.create(),
    },
})

TRY_DB = try_spec.TryDatabase.create({
    'fake-try-group': {
        'fake-try-builder':
            try_spec.TrySpec.create_for_single_mirror('fake-group',
                                                      'fake-builder'),
    },
})


def RunSteps(api):
  api.chromium_tests.lookup_builder()


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(builder_group='fake-group', builder='fake-builder'),
      api.chromium_tests.builders(BOT_DB),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_group_config',
      api.chromium.ci_build(
          builder_group='fake-group2', builder='fake-builder2'),
      api.chromium_tests.builders(BOT_DB),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_builder_config',
      api.chromium.ci_build(
          builder_group='fake-group', builder='fake-builder2'),
      api.chromium_tests.builders(BOT_DB),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'try-builder',
      api.chromium.try_build(
          builder_group='fake-try-group', builder='fake-try-builder'),
      api.chromium_tests.builders(BOT_DB),
      api.chromium_tests.trybots(TRY_DB),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

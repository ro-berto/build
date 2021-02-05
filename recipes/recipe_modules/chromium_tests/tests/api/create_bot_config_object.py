# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec

DEPS = [
    'chromium',
    'chromium_tests',
]


def RunSteps(api):
  api.chromium_tests.create_bot_config_object(
      [api.chromium.get_builder_id()],
      builders=bot_db.BotDatabase.create({
          'chromium.foo': {
              'Foo Builder': bot_spec.BotSpec.create(),
          },
      }))


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='chromium.foo', builder='Foo Builder'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_group_config',
      api.chromium.ci_build(
          builder_group='chromium.bar', builder='Bar Builder'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_builder_config',
      api.chromium.ci_build(
          builder_group='chromium.foo', builder='Bar Builder'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

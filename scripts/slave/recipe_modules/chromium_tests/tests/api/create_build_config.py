# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/json',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec


def RunSteps(api):
  bot = api.chromium_tests.lookup_bot_metadata()
  api.chromium_tests.configure_build(bot.settings)
  api.chromium_tests.prepare_checkout(bot.settings)


def GenTests(api):

  def spec(**kwargs):
    return bot_spec.BotSpec.create(
        chromium_config='chromium', gclient_config='chromium', **kwargs)

  downstream_spec = {
      'fake-builder': {
          'additional_compile_targets': ['foo', 'bar'],
      },
      'fake-builder2': {
          'additional_compile_targets': ['baz', 'shaz'],
      },
  }

  yield api.test(
      'downstream_spec',
      api.chromium.ci_build(mastername='fake-master', builder='fake-builder'),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'fake-master': {
                  'fake-builder': spec(downstream_spec=downstream_spec),
              },
          })),
      api.post_check(post_process.LogEquals,
                     'source side spec migration.fake-master%fake-builder',
                     'downstream_spec',
                     api.json.dumps(downstream_spec, indent=4)),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

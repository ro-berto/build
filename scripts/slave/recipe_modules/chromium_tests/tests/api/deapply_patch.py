# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  bot_config = api.chromium_tests.trybots[
      api.properties['mastername']]['builders'][api.buildbucket.builder_name]
  bot_config_object = api.chromium_tests.create_bot_config_object(
      bot_config['bot_ids'])
  api.chromium_tests.configure_build(bot_config_object)
  update_step, _build_config = api.chromium_tests.prepare_checkout(
      bot_config_object)
  api.chromium_tests.deapply_patch(update_step)


def GenTests(api):
  yield api.test(
      'basic',
      api.platform.name('win'),
      api.chromium.try_build(
          mastername='tryserver.chromium.win', builder='win7-rel'),
  )

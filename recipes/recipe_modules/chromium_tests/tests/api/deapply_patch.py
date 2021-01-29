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
  builder_id = api.chromium.get_builder_id()
  try_spec = api.chromium_tests.trybots[builder_id]
  bot_config = api.chromium_tests.create_bot_config_object(try_spec.mirrors)
  api.chromium_tests.configure_build(bot_config)
  update_step, _ = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.deapply_patch(update_step, 'testing/rts_exclude_file.txt')


def GenTests(api):
  yield api.test(
      'basic',
      api.platform.name('win'),
      api.chromium.try_build(
          builder_group='tryserver.chromium.win',
          builder='win7-rel',
      ),
  )

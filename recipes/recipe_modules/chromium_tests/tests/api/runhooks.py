# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  try_spec = api.chromium_tests.trybots[builder_id]
  bot_config = api.chromium_tests.create_bot_config_object(try_spec.mirrors)
  api.chromium_tests.configure_build(bot_config)

  update_step = api.chromium_checkout.ensure_checkout(bot_config)
  api.chromium_tests.runhooks(update_step)


def GenTests(api):
  yield api.test(
      'failure',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.override_step_data('gclient runhooks (with patch)', retcode=1),
  )

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
  _, bot_config = api.chromium_tests.lookup_builder()
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

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_checkout',
    'chromium_tests',
    'recipe_engine/properties',
]


def RunSteps(api):
  bot_config = api.chromium_tests.trybots[
      api.properties['mastername']]['builders'][api.properties['buildername']]
  bot_config_object = api.chromium_tests.create_generalized_bot_config_object(
      bot_config['bot_ids'])
  api.chromium_tests.configure_build(bot_config_object)

  update_step = api.chromium_checkout.ensure_checkout(bot_config_object)
  api.chromium_tests.runhooks(update_step)


def GenTests(api):
  yield (
      api.test('failure') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
      api.override_step_data('gclient runhooks (with patch)', retcode=1)
  )

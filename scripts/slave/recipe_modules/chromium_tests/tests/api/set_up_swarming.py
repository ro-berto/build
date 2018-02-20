# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'recipe_engine/platform',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium_tests.set_up_swarming(api.properties['bot_config'])


def GenTests(api):
  yield (
      api.test('basic') +
      api.platform.name('win') +
      api.properties(bot_config=api.chromium_tests.bot_config({
          'isolate_server': 'https://example/isolate',
          'swarming_server': 'https://example/swarming',
          'swarming_dimensions': {'os': 'Windows'},
          'swarming_service_account': 'chromium-builder'
      }))
  )

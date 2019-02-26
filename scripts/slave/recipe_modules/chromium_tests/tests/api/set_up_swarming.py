# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_swarming',
    'chromium_tests',
    'isolate',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/runtime',
]

from recipe_engine import post_process


def RunSteps(api):
  api.chromium_tests.set_up_swarming(api.properties['bot_config'])
  api.python.succeeding_step(
      'swarming_service_account', api.chromium_swarming.service_account_json)
  api.python.succeeding_step(
      'isolate_service_account', api.isolate.service_account_json)


def GenTests(api):
  yield (
      api.test('basic') +
      api.platform.name('win') +
      api.properties(bot_config=api.chromium_tests.bot_config({
          'isolate_server': 'https://example/isolate',
          'isolate_service_account': 'chromium_builder',
          'swarming_server': 'https://example/swarming',
          'swarming_dimensions': {'os': 'Windows'},
          'swarming_service_account': 'chromium-builder'
      })) +
      api.runtime(is_luci=False, is_experimental=False) +
      api.post_process(
          post_process.StepTextContains,
          'swarming_service_account',
          ['chromium-builder']) +
      api.post_process(
          post_process.StepTextContains,
          'swarming_service_account',
          ['chromium-builder'])
  )

  yield (
      api.test('luci') +
      api.platform.name('linux') +
      api.properties(bot_config=api.chromium_tests.bot_config({
          'isolate_server': 'https://example/isolate',
          'isolate_service_account': 'chromium_builder',
          'swarming_server': 'https://example/swarming',
          'swarming_dimensions': {'os': 'Ubuntu-14.04'},
          'swarming_service_account': 'chromium-builder'
      })) +
      api.runtime(is_luci=True, is_experimental=False) +
      api.post_process(
          post_process.StepTextEquals,
          'swarming_service_account',
          '') +
      api.post_process(
          post_process.StepTextEquals,
          'swarming_service_account',
          '') +
      api.post_process(post_process.DropExpectation)
  )

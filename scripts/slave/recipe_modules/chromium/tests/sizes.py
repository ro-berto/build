# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
  'chromium',
  'recipe_engine/properties',
  'recipe_engine/runtime',
]


def RunSteps(api):
  api.chromium.set_config('chromium_clang')

  api.chromium.compile()

  api.chromium.sizes(
      platform=api.properties.get('platform'),
      perf_id='test-perf-id',
      results_url='https://example/url')


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id')
  )

  yield (
      api.test('luci') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.post_process(
          post_process.StepCommandContains, 'sizes', ['--use-histograms']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('platform') +
      api.properties(
          platform='linux',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id')
  )

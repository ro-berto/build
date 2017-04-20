# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'recipe_engine/properties',
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
      api.test('platform') +
      api.properties(
          platform='linux',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id')
  )

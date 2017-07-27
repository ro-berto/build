# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.set_config('main_builder')
  api.chromium_android.run_instrumentation_suite(
      'test_suite',
      num_retries=5,
      tool='test_tool',
      verbose=True,
      trace_output=api.properties.get('trace_output'))


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          buildername='test_buildername',
          buildnumber=1337,
          trace_output=False)
  )

  yield (
      api.test('basic_with_tracing') +
      api.properties(
          buildername='test_buildername',
          buildnumber=1337,
          trace_output=True)
  )

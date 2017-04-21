# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_android',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium_android.set_config('main_builder')
  api.chromium_android.incremental_coverage_report()


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          buildbotURL='https://example/url',
          buildername='test_buildername',
          buildnumber=123)
  )

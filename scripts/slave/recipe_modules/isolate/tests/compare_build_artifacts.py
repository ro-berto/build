# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'isolate',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config('chromium')

  api.isolate.compare_build_artifacts('first_dir', 'second_dir')


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123)
  )

  yield (
      api.test('failure') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123) +
      api.step_data('compare_build_artifacts', retcode=1)
  )

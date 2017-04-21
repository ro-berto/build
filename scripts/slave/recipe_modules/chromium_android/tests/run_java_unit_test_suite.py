# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_android',
    'recipe_engine/json',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.set_config('main_builder', BUILD_CONFIG='Release')
  api.chromium_android.run_java_unit_test_suite(
      'test_suite',
      json_results_file=api.json.output())


def GenTests(api):
  yield api.test('basic')

# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_android',
    'recipe_engine/properties',
    'test_utils'
]


def RunSteps(api):
  api.chromium.set_config('android', TARGET_PLATFORM='android')
  api.chromium_android.set_config('main_builder')
  api.chromium_android.run_webview_cts("N", "arm64",
                                       **api.properties['cts_args'])


def GenTests(api):
  yield (
      api.test('basic pass') +
      api.properties.generic(cts_args={}) +
      api.step_data("Run CTS", api.test_utils.canned_gtest_output(passing=True))
  )
  yield (
      api.test('basic fail') +
      api.properties.generic(cts_args={}) +
      api.step_data("Run CTS", api.test_utils.canned_gtest_output(passing=False))
  )
  yield (
      api.test('with suffix') +
      api.properties.generic(cts_args={'suffix': 'build suffix'}) +
      api.step_data("Run CTS (build suffix)", api.test_utils.canned_gtest_output(passing=True))
  )
  yield (
      api.test('with commandline args') +
      api.properties.generic(cts_args={'command_line_args': ['--webview-test-flag']}) +
      api.step_data("Run CTS", api.test_utils.canned_gtest_output(passing=True))
  )
  yield (
      api.test('with details pass') +
      api.properties.generic(cts_args={'result_details': True}) +
      api.step_data("Run CTS", api.test_utils.canned_gtest_output(passing=True))
  )
  yield (
      api.test('with details fail') +
      api.properties.generic(cts_args={'result_details': True}) +
      api.step_data("Run CTS", api.test_utils.canned_gtest_output(passing=False))
  )
  yield (
      api.test('with results file pass') +
      api.properties.generic(cts_args={'json_results_file': '/path/to/a/json/file'}) +
      api.step_data("Run CTS", api.test_utils.canned_gtest_output(passing=True))
  )
  yield (
      api.test('with results file fail') +
      api.properties.generic(cts_args={'json_results_file': '/path/to/a/json/file'}) +
      api.step_data("Run CTS", api.test_utils.canned_gtest_output(passing=False))
  )

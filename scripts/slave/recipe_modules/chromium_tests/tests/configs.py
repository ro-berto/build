# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/gclient',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.gclient.set_config(api.properties.get('gclient_config', 'chromium'))
  api.chromium.set_config(api.properties.get('chromium_config', 'chromium'))
  if 'chromium_tests_config' in api.properties:
    api.chromium_tests.set_config(
        api.properties['chromium_tests_config'])


def GenTests(api):
  yield (
      api.test('chromium_perf_clang') +
      api.properties(
          gclient_config='chromium_perf_clang',
          chromium_config='chromium_perf_clang') +
      api.post_process(post_process.DropExpectation)
  )
  yield (
      api.test('code_coverage_trybot') +
      api.properties(
          chromium_tests_config='code_coverage_trybot',
      ) +
      api.post_process(post_process.DropExpectation)
  )

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'recipe_engine/json',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium_tests.main_waterfall_steps()


def GenTests(api):
  yield (
      api.test('builder') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Builder')
  )

  yield (
      api.test('tester') +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          parent_buildername='Linux Builder') +
      api.override_step_data(
          'read test spec (chromium.linux.json)',
          api.json.output({
              'Linux Tests': {
                  'gtest_tests': ['base_unittests'],
              },
          })
      )
  )

# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_tests',
    'recipe_engine/properties',
    'recipe_engine/step',
]

from RECIPE_MODULES.build.chromium_tests import steps


def RunSteps(api):
  tests = [
      steps.MockTestSpec.create('MockTest').get_test(api.chromium_tests),
      steps.SwarmingGTestTestSpec.create('SwarmingGTestTestSpec').get_test(
          api.chromium_tests),
      steps.LocalGTestTestSpec.create('LocalGTestTestSpec').get_test(
          api.chromium_tests),
  ]

  for test in tests:
    test.inverted_raw_cmd = ['run', 'inverted.filter']
    if test.has_inverted:
      test.is_inverted_rts = True
      assert ('inverted.filter' in test.inverted_raw_cmd)


def GenTests(api):
  yield api.test('basic')

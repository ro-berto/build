# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from recipe_engine import post_process
from recipe_engine.recipe_api import Property
from RECIPE_MODULES.build.chromium_tests import steps

DEPS = [
    'recipe_engine/assertions',
    'recipe_engine/properties',
    'chromium_tests',
]

PROPERTIES = {
    'known_flaky_failures': Property(kind=set),
    'weak_flaky_failures': Property(kind=set),
}

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps


def RunSteps(api, known_flaky_failures, weak_flaky_failures):
  test_spec = steps.SwarmingIsolatedScriptTestSpec.create('failing_suite')
  test = test_spec.get_test(api.chromium_tests)
  test.add_known_luci_analysis_flaky_failures(known_flaky_failures)

  for weak_flake in weak_flaky_failures:
    test.add_weak_luci_analysis_flaky_failure(weak_flake)

  api.assertions.assertSetEqual(test.known_luci_analysis_flaky_failures,
                                known_flaky_failures)
  api.assertions.assertSetEqual(test.weak_luci_analysis_flaky_failures,
                                weak_flaky_failures)


def GenTests(api):
  yield api.test(
      'basic',
      api.properties(
          known_flaky_failures={'testA', 'testB'},
          weak_flaky_failures={'testC', 'testD'}),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
This is essentially a copy of the chromium_trybot recipe. It's being actively
used to experiment with other ways to give chromium developers easier ways to
debug changes. Do not use without talking to martiniss@.
"""

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  with api.chromium.chromium_layout():
    return api.chromium_tests.trybot_steps_for_tests(
        builder_id, builder_config, tests=api.properties.get('tests'))


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium_tests_builder_config.try_build(),
      api.post_process(post_process.DropExpectation),
  )

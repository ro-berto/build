# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
This is essentially a copy of the chromium_trybot recipe. It's being actively
used to experiment with other ways to give chromium developers easier ways to
debug changes. Do not use without talking to martiniss@.
"""

from recipe_engine import post_process

DEPS = [
    'build',
    'chromium',
    'chromium_android',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/gerrit',
    'depot_tools/tryserver',
    'filter',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/runtime',
    'test_results',
    'test_utils',
]


def RunSteps(api):  # pragma: no cover
  with api.chromium.chromium_layout():
    return api.chromium_tests.trybot_steps_for_tests(
        tests=api.properties.get('tests'))


def GenTests(api):
  yield api.test('basic', api.post_process(post_process.DropExpectation))

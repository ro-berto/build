# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'test_utils',
    'recipe_engine/properties',
]


def RunSteps(api):
  results = api.test_utils.create_results_from_json(
      api.properties['results_json'])
  results.as_jsonish()

def GenTests(api):
  yield (
      api.test('results_none') +
      api.properties(results_json=None) +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

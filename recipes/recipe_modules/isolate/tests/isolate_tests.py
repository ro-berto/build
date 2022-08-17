# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

DEPS = [
    'isolate',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/buildbucket',
]

def RunSteps(api):
  api.isolate.isolate_tests(
      api.path['checkout'].join('out', 'Release'),
      targets=['dummy_target_1', 'dummy_target_2'])


def GenTests(api):
  yield api.test('basic')

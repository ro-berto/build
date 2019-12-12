# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.assertions.assertNotEqual(
      len(api.buildbucket.build.input.gerrit_changes), 0)
  api.assertions.assertEqual(
      api.properties.get('mastername', None), 'fake-master')


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.try_build(mastername='fake-master'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

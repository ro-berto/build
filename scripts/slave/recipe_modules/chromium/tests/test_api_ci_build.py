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
  api.assertions.assertTrue(
      api.buildbucket.build.input.HasField('gitiles_commit'))
  api.assertions.assertEqual(
      api.properties.get('mastername', None), 'fake-master')
  api.assertions.assertEqual(
      api.properties.get('parent_mastername', None),
      api.properties['expected_parent_mastername'])
  api.assertions.assertEqual(
      api.properties.get('parent_buildername', None),
      api.properties['expected_parent_buildername'])


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(mastername='fake-master'),
      api.properties(
          expected_parent_mastername=None,
          expected_parent_buildername=None,
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'parent-builder',
      api.chromium.ci_build(
          mastername='fake-master',
          parent_buildername='fake-parent',
      ),
      api.properties(
          expected_parent_mastername='fake-master',
          expected_parent_buildername='fake-parent',
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'parent-builder-and-master',
      api.chromium.ci_build(
          mastername='fake-master',
          parent_mastername='fake-parent-master',
          parent_buildername='fake-parent',
      ),
      api.properties(
          expected_parent_mastername='fake-parent-master',
          expected_parent_buildername='fake-parent',
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

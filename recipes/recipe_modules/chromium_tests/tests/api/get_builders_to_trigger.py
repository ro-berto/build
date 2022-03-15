# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import six

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/assertions',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  api.chromium_tests.configure_build(builder_config)
  actual = api.chromium_tests._get_builders_to_trigger(builder_id,
                                                       builder_config)
  expected = api.properties['expected']
  api.assertions.assertCountEqual(actual, expected)


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Builder',
      ),
      api.properties(expected=['Linux Tests']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'dedup',
      api.chromium_tests_builder_config.ci_build(
          builder_group='fake-group',
          builder='fake-builder',
          # Multiple entries for 'fake-tester' in different builder
          # groups, as would be the case when making a copy for changing
          # the builder group
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(),
                  'fake-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='fake-builder',
                      ),
              },
              'fake-group2': {
                  'fake-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_builder_group='fake-group',
                          parent_buildername='fake-builder',
                      ),
              },
          })),
      api.properties(expected=['fake-tester']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test recipe for invalid use of property builders of the test API."""

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium_tests_builder_config',
    'recipe_engine/assertions',
    'recipe_engine/json',
    'recipe_engine/properties',
]


def RunSteps(api):
  ctbc_test_api = api.chromium_tests_builder_config.test_api

  # Building tester without specifying parent
  props_builder = ctbc_test_api.properties_builder_for_ci_tester(
      builder_group='fake-group', builder='fake-tester')
  with api.assertions.assertRaises(TypeError) as caught:
    props_builder.build()
  api.assertions.assertEqual(
      str(caught.exception),
      '`with_parent` must be called before calling `build`')

  # Specifying parent multiple times
  props_builder = ctbc_test_api \
      .properties_builder_for_ci_tester(
          builder_group='fake-group', builder='fake-tester') \
      .with_parent(builder_group='fake-group', builder='fake-builder')
  with api.assertions.assertRaises(TypeError) as caught:
    props_builder.with_parent(
        builder_group='fake-group', builder='fake-builder')
  api.assertions.assertEqual(
      str(caught.exception), '`with_parent` can only be called once')


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/json',
    'recipe_engine/properties',
    'test_results',
]

from recipe_engine import post_process

def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')
  api.test_results.set_config('public_server')

  update_step = api.bot_update.ensure_checkout()

  single_spec = api.properties.get('single_spec')
  test_spec = single_spec if single_spec else {}

  test_args = api.chromium_tests.steps.get_args_for_test(
      api,
      api.chromium_tests,
      test_spec,
      update_step
  )
  if api.properties.get('expected_args'):
    # For some reason, we get expected_args as a tuple instead of a list
    assert list(api.properties.get('expected_args')) == test_args


def GenTests(api):
  yield (
      api.test('buildbucket_string') +
      api.properties(
          single_spec={
              'args': ['${buildbucket_build_id}'],
              'test': 'base_unittests',
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildbucket='{"build": {"id": "12345"}}',
          expected_args=[u"12345"],
      ) +
      api.post_process(post_process.StatusCodeIn, 0) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('buildbucket_unicode') +
      api.properties(
          single_spec={
              'args': ['${buildbucket_build_id}'],
              'test': 'base_unittests',
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildbucket=u'{"build": {"id": "12345"}}',
          expected_args=[u"12345"],
      ) +
      api.post_process(post_process.StatusCodeIn, 0) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('buildbucket_dictionary') +
      api.properties(
          single_spec={
              'args': ['${buildbucket_build_id}'],
              'test': 'base_unittests',
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildbucket={"build": {"id": "12345"}},
          expected_args=[u"12345"],
      ) +
      api.post_process(post_process.StatusCodeIn, 0) +
      api.post_process(post_process.DropExpectation)
  )
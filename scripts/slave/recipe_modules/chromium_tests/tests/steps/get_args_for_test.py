# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'test_results',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import generators


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')
  api.test_results.set_config('public_server')

  update_step = api.bot_update.ensure_checkout()

  single_spec = api.properties.get('single_spec')
  test_spec = single_spec if single_spec else {}

  test_args = generators.get_args_for_test(api, api.chromium_tests, test_spec,
                                           update_step)
  if api.properties.get('expected_args'):
    # For some reason, we get expected_args as a tuple instead of a list
    api.assertions.assertEqual(
        list(api.properties.get('expected_args')), test_args)


def GenTests(api):
  yield api.test(
      'buildbucket_string',
      api.properties(
          single_spec={
              'args': ['${buildbucket_build_id}'],
              'test': 'base_unittests',
          },
          mastername='test_mastername',
          expected_args=[u'8945511751514863184'],
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'buildbucket_unicode',
      api.properties(
          single_spec={
              'args': ['${buildbucket_build_id}'],
              'test': 'base_unittests',
          },
          mastername='test_mastername',
          expected_args=[u'8945511751514863184'],
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'buildbucket_dictionary',
      api.properties(
          single_spec={
              'args': ['${buildbucket_build_id}'],
              'test': 'base_unittests',
          },
          mastername='test_mastername',
          expected_args=[u'8945511751514863184'],
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

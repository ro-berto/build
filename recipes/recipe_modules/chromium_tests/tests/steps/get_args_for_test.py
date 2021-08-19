# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/assertions',
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

  test_args = generators.get_args_for_test(api.chromium_tests, test_spec,
                                           update_step)
  if 'expected_args' in api.properties:
    # For some reason, we get expected_args as a tuple instead of a list
    api.assertions.assertEqual(
        list(api.properties.get('expected_args')), test_args)


def GenTests(api):
  yield api.test(
      'buildbucket_string',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'args': ['${buildbucket_build_id}'],
              'test': 'base_unittests',
          },
          expected_args=[u'8945511751514863184'],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'buildbucket_unicode',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'args': ['${buildbucket_build_id}'],
              'test': 'base_unittests',
          },
          expected_args=[u'8945511751514863184'],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'buildbucket_dictionary',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'args': ['${buildbucket_build_id}'],
              'test': 'base_unittests',
          },
          expected_args=[u'8945511751514863184'],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'conditional args added',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'conditional_args': [{
                  'variable': 'buildbucket_project',
                  'value': 'chromium',
                  'args': ['foo', 'bar'],
              }],
          },
          expected_args=['foo', 'bar'],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'conditional args not added',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'conditional_args': [{
                  'variable': 'buildbucket_project',
                  'value': 'chrome',
                  'args': ['foo', 'bar'],
              }],
          },
          expected_args=[],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'inverted conditional args added',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'conditional_args': [{
                  'variable': 'buildbucket_project',
                  'value': 'chrome',
                  'invert': True,
                  'args': ['foo', 'bar'],
              }],
          },
          expected_args=['foo', 'bar'],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'inverted conditional args not added',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'conditional_args': [{
                  'variable': 'buildbucket_project',
                  'value': 'chromium',
                  'invert': True,
                  'args': ['foo', 'bar'],
              }],
          },
          expected_args=[],
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'conditional args without variable',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(single_spec={
          'conditional_args': [{}],
      }),
      api.post_process(post_process.StatusException),
      api.post_check(lambda check, steps: \
          check("Conditional has no 'variable' key"
                in steps['Invalid conditional'].step_text)),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'conditional args with unknown variable',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(single_spec={
          'conditional_args': [{
              'variable': 'foobar',
          }],
      }),
      api.post_process(post_process.StatusException),
      api.post_check(lambda check, steps: \
          check("Unknown variable 'foobar'"
                in steps['Invalid conditional'].step_text)),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
    'chromium_tests',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps

PROPERTIES = {
    # This property is a dictionary that specifies the expectations of the
    # labeled known flakes of the mocked tests, and the format is from a test
    # name to a list of tests.
    'known_flakes_expectations': Property(default={}),

    # This property is a boolean that indicates whether to create a mocked test
    # that has failed tests to test that if there are no test failures, a
    # request should NOT be sent to the service because it's unnecessary.
    'exclude_failed_test': Property(default=False),

    # This property is a boolean that indicates whether to create a mocked test
    # that has a massive amount of failures to test that a request should NOT be
    # sent to the service to avoid overloading it.
    'has_too_many_failures': Property(default=False),
}


def RunSteps(api, known_flakes_expectations, exclude_failed_test,
             has_too_many_failures):
  tests = [
      steps.MockTest(name='succeeded_test', api=api),
      steps.MockTest(
          name='invalid_test',
          api=api,
          runs_on_swarming=True,
          has_valid_results=False),
  ]

  if not exclude_failed_test:
    tests.append(
        steps.MockTest(
            name='failed_test',
            api=api,
            runs_on_swarming=True,
            per_suffix_failures={'with patch': ['testA', 'testB']},
        ))

  if has_too_many_failures:
    tests.append(
        steps.MockTest(
            name='too_many_failures',
            api=api,
            runs_on_swarming=True,
            per_suffix_failures={
                'with patch': ['test%d' % i for i in range(1000)]
            }))

  api.test_utils.run_tests(
      api.chromium_tests.m,
      tests,
      'with patch',
      retry_failed_shards=True,
      retry_invalid_shards=True)

  for t in tests:
    assert t.known_flaky_failures == set(
        known_flakes_expectations.get(t.name, []))


def GenTests(api):

  yield api.test(
      'immune to infra failure of querying flaky failures',
      api.properties(
          mastername='m',
          buildername='b',
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data('exonerate known flaky failures', retcode=1),
      api.post_process(post_process.MustRun, 'exonerate known flaky failures'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'immune to ill-formed response',
      api.properties(
          mastername='m',
          buildername='b',
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data(
          'exonerate known flaky failures',
          api.json.output([{
              'step_ui_name': 'browser_tests (with patch)'
          }])),
      api.post_process(post_process.MustRun, 'exonerate known flaky failures'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no failed tests',
      api.properties(
          mastername='m',
          buildername='b',
          exclude_failed_test=True,
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.post_process(post_process.DoesNotRun,
                       'exonerate known flaky failures'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no tests are marked as known flaky',
      api.properties(
          mastername='m',
          buildername='b',
          known_flakes_expectations={},
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data('exonerate known flaky failures', api.json.output([])),
      api.post_process(post_process.MustRun, 'exonerate known flaky failures'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'part of the tests are marked as known flaky',
      api.properties(
          mastername='m',
          buildername='b',
          known_flakes_expectations={
              'failed_test': ['testA'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data(
          'exonerate known flaky failures',
          api.json.output([{
              'step_ui_name': 'failed_test (with patch)',
              'test_name': 'testA',
              'affected_gerrit_changes': ['123', '234'],
          }])),
      api.post_process(post_process.MustRun, 'exonerate known flaky failures'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'all of the tests are marked as known flaky',
      api.properties(
          mastername='m',
          buildername='b',
          known_flakes_expectations={
              'failed_test': ['testA', 'testB'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data(
          'exonerate known flaky failures',
          api.json.output([{
              'step_ui_name': 'failed_test (with patch)',
              'test_name': 'testA',
              'affected_gerrit_changes': ['123', '234'],
          },
                           {
                               'step_ui_name': 'failed_test (with patch)',
                               'test_name': 'testB',
                               'affected_gerrit_changes': ['567', '678'],
                           }])),
      api.post_process(post_process.MustRun, 'exonerate known flaky failures'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip querying if there are too many failures',
      api.properties(
          mastername='m',
          buildername='b',
          has_too_many_failures=True,
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.post_process(post_process.DoesNotRun,
                       'exonerate known flaky failures'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

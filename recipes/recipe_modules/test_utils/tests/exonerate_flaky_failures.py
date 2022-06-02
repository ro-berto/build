# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'chromium',
    'chromium_tests',
    'test_utils',
]

from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.build.weetbix.api import CLUSTER_STEP_NAME

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
  test_specs = [
      steps.MockTestSpec.create(name='succeeded_test'),
      steps.MockTestSpec.create(
          name='invalid_test', runs_on_swarming=True, has_valid_results=False),
  ]

  if not exclude_failed_test:
    test_specs.append(
        steps.MockTestSpec.create(
            name='failed_test',
            runs_on_swarming=True,
            per_suffix_failures={'with patch': ['testA', 'testB']},
            invocation_names=['invocations/whatever'],
        ))

  if has_too_many_failures:
    test_specs.append(
        steps.MockTestSpec.create(
            name='too_many_failures',
            runs_on_swarming=True,
            per_suffix_failures={
                'with patch': ['test%d' % i for i in range(1000)]
            }))

  tests = [s.get_test(api.chromium_tests) for s in test_specs]

  api.test_utils.run_tests(
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
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.step_data('query known flaky failures on CQ', retcode=1),
      api.post_process(post_process.MustRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.StepTextContains,
                       'query known flaky failures on CQ',
                       ['Failed to get known flakes']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'immune to ill-formed response',
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({'step_ui_name': 'browser_tests (with patch)'})),
      api.post_process(post_process.StepTextContains,
                       'query known flaky failures on CQ',
                       ['Response is ill-formed']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'immune to another ill-formed response',
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output(
              {'flakes': [{
                  'step_ui_name': 'browser_tests (with patch)'
              }]})),
      api.post_process(post_process.StepTextContains,
                       'query known flaky failures on CQ',
                       ['Response is ill-formed']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'empty response',
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.properties(**{
          '$build/test_utils': {
              'should_exonerate_flaky_failures': True,
          },
      }),
      api.step_data('query known flaky failures on CQ', api.json.output({})),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no failed tests',
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.properties(
          exclude_failed_test=True,
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.post_process(post_process.DoesNotRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no tests are marked as known flaky',
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.properties(
          known_flakes_expectations={},
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data('query known flaky failures on CQ', api.json.output([])),
      api.post_process(post_process.MustRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  def CheckStepInput(check, step_odict, step_name, test_name):
    step = step_odict[step_name]
    check(test_name in step.stdin)

  yield api.test(
      'part of the tests are marked as known flaky',
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA']))),
      api.properties(
          known_flakes_expectations={
              'failed_test': ['testA'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [{
                  'test': {
                      'step_ui_name': 'failed_test (with patch)',
                      'test_name': 'testA',
                  },
                  'affected_gerrit_changes': ['123', '234'],
                  'monorail_issue': '999',
              }]
          })),
      api.post_process(post_process.MustRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.MustRun,
                       'exonerate unrelated test failures'),
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'testA'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'all of the tests are marked as known flaky',
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA', 'testB']))),
      api.properties(
          known_flakes_expectations={
              'failed_test': ['testA', 'testB'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [
                  {
                      'test': {
                          'step_ui_name': 'failed_test (with patch)',
                          'test_name': 'testA',
                      },
                      'affected_gerrit_changes': ['123', '234'],
                      'monorail_issue': '999',
                  },
                  {
                      'test': {
                          'step_ui_name': 'failed_test (with patch)',
                          'test_name': 'testB',
                      },
                      'affected_gerrit_changes': ['567', '678'],
                      'monorail_issue': '998',
                  },
              ]
          })),
      api.post_process(post_process.MustRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.MustRun,
                       'exonerate unrelated test failures'),
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'testA'),
      api.post_process(CheckStepInput, 'exonerate unrelated test failures',
                       'testB'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cluster failures with weetbix',
      api.chromium.generic_build(
          builder_group='g',
          builder='b',
          experiments=['enable_weetbix_queries'],
      ),
      api.override_step_data(
          'failed_test results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'failed_test', failing_tests=['testA']))),
      api.properties(
          known_flakes_expectations={
              'failed_test': ['testA'],
          },
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.step_data(
          'query known flaky failures on CQ',
          api.json.output({
              'flakes': [{
                  'test': {
                      'step_ui_name': 'failed_test (with patch)',
                      'test_name': 'testA',
                  },
                  'affected_gerrit_changes': ['123', '234'],
                  'monorail_issue': '999',
              }],
          })),
      api.step_data(
          CLUSTER_STEP_NAME + '.rpc call',
          stdout=api.raw_io.output_text(
              api.json.dumps({
                  'clusteredTestResults': [{
                      'requestTag':
                          'testA_reason_0',
                      'clusters': [{
                          'clusterId': {
                              'algorithm': 'reason-v3',
                              'id': 'fa4a547e837c48d87ea1f9dfb3d44173',
                              'bug': {
                                  'system':
                                      'monorail',
                                  'id':
                                      '12345',
                                  'link_text':
                                      'crbug.com/12345',
                                  'url': ('bugs.chromium.org/p/chromium/issues/'
                                          'detail?id=12345'),
                              },
                          },
                      }],
                  }],
              }))),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip querying if there are too many failures',
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.properties(
          exclude_failed_test=True,
          has_too_many_failures=True,
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.post_process(post_process.DoesNotRun,
                       'query known flaky failures on CQ'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  # The difference between this test and the immediate above one is that this
  # test doesn't exclude the test suite with limited number of failures, and
  # this test tests that even though there are tests with too many failures, the
  # recipe should still query known flaky failures for other test suites with
  # limited number of failures.
  yield api.test(
      'keep querying if at least one test suite has limited failures',
      api.chromium.generic_build(builder_group='g', builder='b'),
      api.properties(
          has_too_many_failures=True,
          **{
              '$build/test_utils': {
                  'should_exonerate_flaky_failures': True,
              },
          }),
      api.post_process(post_process.LogContains,
                       'query known flaky failures on CQ', 'input',
                       ['failed_test (with patch)']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

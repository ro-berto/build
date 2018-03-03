# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
import json

from recipe_engine.config import Dict
from recipe_engine.config import List
from recipe_engine.config import Single
from recipe_engine.recipe_api import Property


DEPS = [
    'adb',
    'chromium',
    'chromium_android',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'commit_position',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/git',
    'filter',
    'findit',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/context',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'swarming',
    'test_results',
    'test_utils',
]


PROPERTIES = {
    'target_mastername': Property(
        kind=str, help='The target master to match compile config to.'),
    'target_testername': Property(
        kind=str,
        help='The target tester to match test config to. If the tests are run '
             'on a builder, just treat the builder as a tester.'),
    'test_revision': Property(
        kind=str, help='The revision to test.'),
    'tests': Property(
        kind=Dict(value_type=list),
        default={},
        help='The failed tests, the test name should be full name, e.g.: {'
             '  "browser_tests": ['
             '    "suite.test1", "suite.test2"'
             '  ]'
             '}'),
    'buildbucket': Property(
        default=None,
        help='The buildbucket property in which we can find build id.'
             'We need to use build id to get tests.'),
    'test_repeat_count': Property(
        kind=Single(int, required=False), default=100,
        help='How many times to repeat the tests.'),
    'skip_tests': Property(
        kind=Single(bool, required=False), default=False,
        help='If True, skip the execution of the tests.'),
}


def RunSteps(api, target_mastername, target_testername,
             test_revision, tests, buildbucket, test_repeat_count, skip_tests):

  tests, target_buildername, checked_out_revision, cached_revision  = (
      api.findit.configure_and_sync(api, tests, buildbucket, target_mastername,
                                    target_testername, test_revision))

  test_results = {}
  report = {
      'result': test_results,
      'metadata': {},
      'previously_cached_revision': cached_revision,
      'previously_checked_out_revision': checked_out_revision
  }

  try:
    test_results[test_revision], _ = (
        api.findit.compile_and_test_at_revision(
          api, target_mastername, target_buildername, target_testername,
          test_revision, tests, False, test_repeat_count, skip_tests))
  except api.step.InfraFailure:
    test_results[test_revision] = api.findit.TestResult.INFRA_FAILED
    report['metadata']['infra_failure'] = True
    raise
  finally:
    report['last_checked_out_revision'] = api.properties.get('got_revision')
    report['isolated_tests'] = api.isolate.isolated_tests
    # Give the full report including test results and metadata.
    api.python.succeeding_step(
        'report', [json.dumps(report, indent=2)], as_log='report')

  return report


def GenTests(api):
  def props(
      tests, platform_name, tester_name, use_analyze=False, revision=None,
      buildbucket=None, skip_tests=False):
    properties = {
        'path_config': 'kitchen',
        'mastername': 'tryserver.chromium.%s' % platform_name,
        'buildername': '%s_chromium_variable' % platform_name,
        'bot_id': 'build1-a1',
        'buildnumber': 1,
        'target_mastername': 'chromium.%s' % platform_name,
        'target_testername': tester_name,
        'test_revision': revision or 'r0',
        'skip_tests': skip_tests,
    }
    if tests:
      properties['tests'] = tests
    if buildbucket:
      properties['buildbucket'] = buildbucket
    return api.properties(**properties) + api.platform.name(platform_name)

  yield (
      api.test('flakiness_isolate_only') +
      props({'browser_tests': ['Test.One']}, 'mac', 'Mac10.13 Tests', skip_tests=True) +
      api.override_step_data(
          'test r0.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.13 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'browser_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 10},
                      },
                  ],
              },
          })
      )
  )
  yield (
      api.test('flakiness_swarming_tests') +
      props({'browser_tests': ['Test.One']}, 'mac', 'Mac10.13 Tests') +
      api.override_step_data(
          'test r0.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.13 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'browser_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 10},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r0.browser_tests (r0)',
          api.swarming.canned_summary_output() +
          api.test_utils.simulated_gtest_output(passed_test_names=['Test.One'])
      )
  )
  yield (
      api.test('flakiness_non-swarming_tests') +
      props({'gl_tests': ['Test.One']}, 'mac', 'Mac10.13 Tests') +
      api.override_step_data(
          'test r0.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.13 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': False},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r0.gl_tests (r0)',
          api.swarming.canned_summary_output() +
          api.test_utils.simulated_gtest_output(passed_test_names=['Test.One'])

      )
  )
  yield (
      api.test('use_build_parameter_for_tests') +
      props({}, 'mac', 'Mac10.13 Tests',
            revision='r0',
            buildbucket=json.dumps({'build': {'id': 1}})) +
      api.buildbucket.simulated_buildbucket_output({
          'additional_build_parameters' : {
              'tests': {
                  'gl_tests': ['Test.One']
              }
          }}) +
      api.override_step_data(
          'test r0.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.13 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r0.gl_tests (r0)',
          api.swarming.canned_summary_output() +
          api.test_utils.simulated_gtest_output(passed_test_names=['Test.One'])
      )
  )
  yield (
      api.test('record_infra_failure') +
      props({'gl_tests': ['Test.One']}, 'mac', 'Mac10.13 Tests') +
      api.override_step_data(
          'test r0.read test spec (chromium.mac.json)',
          api.json.output({
              'Mac10.13 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {'can_use_on_swarming_builders': True},
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'test r0.preprocess_for_goma.start_goma', retcode=1) +
      api.step_data(
          'test r0.preprocess_for_goma.goma_jsonstatus',
          api.json.output(
              data={
                  'notice': [
                      {
                          'infra_status': {
                              'ping_status_code': 408,
                          },
                      },
                  ],
              }))
  )

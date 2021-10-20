# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import Dict
from recipe_engine.config import Single
from recipe_engine.recipe_api import Property
from recipe_engine import post_process

from RECIPE_MODULES.build import chromium


PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'builder_group',
    'chromium_swarming',
    'chromium_tests',
    'findit',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'test_utils',
]


PROPERTIES = {
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
    'test_repeat_count': Property(
        kind=Single(int, required=False), default=100,
        help='How many times to repeat the tests.'),
    'skip_tests': Property(
        kind=Single(bool, required=False), default=False,
        help='If True, skip the execution of the tests.'),
}


def RunSteps(api, target_testername, test_revision, tests, test_repeat_count,
             skip_tests):
  assert tests, 'No failed tests were specified.'

  target_builder_group = api.builder_group.for_target
  target_tester_id = chromium.BuilderId.create_for_group(
      target_builder_group, target_testername)
  bot_mirror, checked_out_revision, cached_revision = (
      api.findit.configure_and_sync(target_tester_id, test_revision))

  test_results = {}
  report = {
      'result': test_results,
      'metadata': {},
      'previously_cached_revision': cached_revision,
      'previously_checked_out_revision': checked_out_revision
  }

  try:
    test_results[test_revision], _, compile_failure = (
        api.findit.compile_and_test_at_revision(bot_mirror, test_revision,
                                                tests, False, test_repeat_count,
                                                skip_tests))
    if compile_failure:
      return compile_failure
  except api.step.InfraFailure:
    test_results[test_revision] = api.findit.TestResult.INFRA_FAILED
    report['metadata']['infra_failure'] = True
    raise
  finally:
    report['last_checked_out_revision'] = api.properties.get('got_revision')
    report['isolated_tests'] = api.isolate.isolated_tests
    # Give the full report including test results and metadata.
    api.python.succeeding_step(
        'report', [api.json.dumps(report, indent=2)], as_log='report')


def GenTests(api):
  def base(
      tests, platform_name, tester_name, use_analyze=False, revision=None,
      skip_tests=False):
    properties = {
        'bot_id': 'build1-a1',
        'target_testername': tester_name,
        'test_revision': revision or 'r0',
        'skip_tests': skip_tests,
    }
    if tests:
      properties['tests'] = tests
    return sum([
        api.properties(**properties),
        api.buildbucket.ci_build(
            builder='findit_variable',
            git_repo='https://chromium.googlesource.com/chromium/src',
        ),
        api.builder_group.for_current('tryserver.chromium.%s' % platform_name),
        api.builder_group.for_target('chromium.%s' % platform_name),
        api.platform.name(platform_name),
    ], api.empty_test_data())

  yield api.test(
      'flakiness_isolate_only',
      base({
          'browser_tests': ['Test.One']
      },
           'mac',
           'Mac10.13 Tests',
           skip_tests=True),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 10
                      },
                  },],
              },
          },
          step_prefix='test r0.'),
  )
  yield api.test(
      'flakiness_swarming_tests',
      base({
          'browser_tests': ['Test.One']
      }, 'mac', 'Mac10.13 Tests'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 10
                      },
                  },],
              },
          },
          step_prefix='test r0.'),
      api.override_step_data(
          'test r0.browser_tests (r0)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One']))),
  )
  yield api.test(
      'flakiness_non-swarming_tests',
      base({'gl_tests': ['Test.One']}, 'mac', 'Mac10.13 Tests'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': False
                      },
                  },],
              },
          },
          step_prefix='test r0.'),
      api.override_step_data(
          'test r0.gl_tests (r0)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_gtest_output(
                  passed_test_names=['Test.One'])),
          api.legacy_annotation.success_step,
          stderr=api.raw_io.output_text(
              'rdb-stream: included "invocations/test-inv" in "build-inv"')),
  )
  yield api.test(
      'record_infra_failure',
      base({
          'gl_tests': ['Test.One']
      }, 'mac', 'Mac10.13 Tests'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          },
          step_prefix='test r0.'),
      api.override_step_data(
          'test r0.preprocess_for_goma.start_goma', retcode=1),
      api.step_data(
          'test r0.preprocess_for_goma.goma_jsonstatus',
          api.json.output(data={
              'notice': [{
                  'infra_status': {
                      'ping_status_code': 408,
                  },
              },],
          })),
  )
  yield api.test(
      'flakiness_blink_web_tests',
      base({
          'blink_web_tests': ['fast/dummy/test.html']
      }, 'mac', 'Mac10.13 Tests'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'blink_web_tests',
                      'name': 'blink_web_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 1,
                      },
                  },],
              },
          },
          step_prefix='test r0.'),
      api.override_step_data(
          'test r0.blink_web_tests (r0)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.simulated_isolated_script_output(
                  flaky_test_names=['fast/dummy/test.html'],
                  path_delimiter='/'))),
  )

  yield api.test(
      'compile_failure',
      base({
          'gl_tests': ['Test.One']
      }, 'mac', 'Mac10.13 Tests'),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'Mac10.13 Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': False
                      },
                  },],
              },
          },
          step_prefix='test r0.'),
      api.step_data('test r0.compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

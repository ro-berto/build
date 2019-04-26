# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/bot_update',
    'ios',
    'perf_dashboard',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/time',
    'test_results',
    'test_utils',
]

import json

from recipe_engine import post_process


def RunSteps(api):
  api.ios.checkout()

  platform = api.properties.get('platform', 'device')
  result_callback = api.properties.get('result_callback', None)
  config = {'device check': True}
  task = {'step name': 'dummy step name',
          'test': {'os': 'dummy OS',
                   'device type': 'iPhone X',
                   'app': None,
                   'use trusted cert': True,
                   'replay package name': 'dummy name',
                   'replay package version': 'dummy version',
                   'expiration_time': 50,
                   'max runtime seconds': 70,
                   },
          'task_id': 'dummy task id',
          'isolated hash': 'dummy isolated hash',
          'xcode build version': 'dummy build version',
          'xcode version': 'dummy xcode version',
          'bot id': 'dummy bot id',
          'pool': 'dummy pool',
          }
  if platform == 'simulator':
    task['test']['optional_dimensions'] = {
        '60': [
            {
              'host os': 'other-dummy-OS',
            }
          ]
        }
  test = api.chromium_tests.steps.SwarmingIosTest(
      'swarming_service_account', platform, config, task,
      upload_test_results=True, result_callback=result_callback,
      use_test_data = True)
  assert test.runs_on_swarming

  test.pre_run(api, '')
  api.ios.collect([test])


def GenTests(api):
  def generate_test_results_placeholder(api, failing_test):
    summary_contents = {
      'logs': {
        'passed tests': ['PASSED_TEST'],
      },
      'step_text': 'dummy step text'
    }
    if failing_test:
      summary_contents['logs']['failed tests'] = ['FAILED_TEST']

    summary_path = '10000/summary.json'
    return api.raw_io.output_dir({summary_path: json.dumps(summary_contents)})

  def generate_passing_test(api, simulator):
    step_name = 'dummy step name on iOS-dummy OS'
    if simulator:
      step_name = 'dummy step name on Mac'
    return api.step_data(
        step_name, generate_test_results_placeholder(api, failing_test=False))

  def generate_failing_summary(state, exit_code):
    return {'shards': [
        {
          'bot_id': 'vm30',
          'completed_ts': '2014-09-25T01:43:11.123',
          'created_ts': '2014-09-25T01:41:00.123',
          'duration': 31.5,
          'exit_code': exit_code,
          'failure': True,
          'task_id': '148aa78d7aa%02d00',
          'internal_failure': False,
          'modified_ts': '2014-09-25 01:42:00',
          'name': 'heartbeat-canary-2014-09-25_01:41:55-os=Windows',
          'output': 'Heart beat succeeded on win32.\n'
          'Foo',
          'outputs_ref': {
            'isolated': 'abc123',
            'isolatedserver': 'https://isolateserver.appspot.com',
            'namespace': 'default-gzip',
          },
          'started_ts': '2014-09-25T01:42:11.123',
          'state': state,
        }
    ]}

  yield (
      api.test('basic') +
      generate_passing_test(api, simulator=False) +
      api.post_process(post_process.StepSuccess,
                       'dummy step name on iOS-dummy OS') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('basic_failure') +
      api.override_step_data(
          'dummy step name on iOS-dummy OS',
          api.chromium_swarming.summary(
              dispatched_task_step_test_data=generate_test_results_placeholder(
                  api, failing_test=True),
              data=generate_failing_summary('COMPLETED', 1),
              retcode=0)) +
      api.post_process(post_process.StepFailure,
                       'dummy step name on iOS-dummy OS') +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('basic_simulator') +
      generate_passing_test(api, simulator=True) +
      api.properties(platform='simulator') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  summary_contents = {
    'logs': {
      'passed tests': ['PASSED_TEST'],
      'flaked tests': ['FLAKED_TEST'],
      'failed tests': ['FAILED_TEST'],
    },
    'step_text': 'dummy step text'
  }
  summary_path = '10000/summary.json'
  yield (
      api.test('test_results_parser') +
      api.step_data(
          'dummy step name on iOS-dummy OS',
          api.raw_io.output_dir({summary_path: json.dumps(summary_contents)})) +
      api.post_process(post_process.StatusFailure) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('perf_results') +
      generate_passing_test(api, simulator=False) +
      api.properties(
        mastername='tryserver.fake',
      ) +
      api.path.exists(
          api.path['cleanup'].join('dummy task id_tmp_1', '10000', 'Documents',
                                 'perf_result.json')) +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('upload_to_flakiness') +
      generate_passing_test(api, simulator=False) +
      api.properties(
        mastername='tryserver.fake',
      ) +
      api.path.exists(
          api.path['cleanup'].join('dummy task id_tmp_1', '10000',
                                   'full_results.json')) +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('host_os_rewritten') +
      generate_passing_test(api, simulator=True) +
      api.properties(
          mastername='tryserver.fake',
          platform='simulator') +
      api.post_process(
          post_process.StepCommandContains,
          '[trigger] dummy step name on Mac',
          ['--optional-dimension', 'os', 'other-dummy-OS', '60']
      ) +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  for state in ['COMPLETED', 'TIMED_OUT', 'EXPIRED', 'DUMMY']:
    for retcode in ['1', 2]:
      yield (
          api.test('shard_failure_' + state + '_' + str(retcode)) +
          api.override_step_data(
              'dummy step name on iOS-dummy OS',
              api.chromium_swarming.summary(
                  dispatched_task_step_test_data=None,
                  data=generate_failing_summary(state, retcode),
                  retcode=int(retcode))) +
          api.post_process(post_process.StatusAnyFailure) +
          api.post_process(post_process.DropExpectation)
      )

  yield (
      api.test('result_callback') +
      generate_passing_test(api, simulator=False) +
      api.properties(
        result_callback=lambda **kw: None,
      ) +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('output_refs') +
      generate_passing_test(api, simulator=False) +
      api.post_process(post_process.StepSuccess,
                       'dummy step name on iOS-dummy OS') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(
          post_process.AnnotationContains, 'dummy step name on iOS-dummy OS',
          ['@@@STEP_LINK@shard #0 isolated out@'
           'https://isolateserver.appspot.com/browse?namespace=default-gzip'
           '&hash=abc123@@@']) +
      api.post_process(post_process.DropExpectation)
  )

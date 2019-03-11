# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import post_process

DEPS = [
    'test_utils',
    'recipe_engine/step',
]


def RunSteps(api):

  step_result = api.step(
      'test', ['test_binary', '--result-json', api.test_utils.gtest_results()],
      ok_ret='all')
  api.test_utils.present_gtest_failures(step_result)


def GenTests(api):

  def has_log(check, step_odict, step, log):
    if not check('step %s was run' % step, step in step_odict):
      return  # pragma: no cover
    logs = post_process.GetLogs(step_odict[step])
    check('step %s has log %s' % (step, log), log in logs)

  def doesnt_have_log(check, step_odict, step, log):
    if not check('step %s was run' % step, step in step_odict):
      return  # pragma: no cover
    logs = post_process.GetLogs(step_odict[step])
    check('step %s does not have log %s' % (step, log), log not in logs)

  yield (
      api.test('failure') +
      api.override_step_data(
          'test',
          api.test_utils.gtest_results(json.dumps({
              'per_iteration_data': [
                  {
                      'Test.One': [
                          {
                              'elapsed_time_ms': 0,
                              'output_snippet': ':(',
                              'status': 'FAILURE',
                          },
                      ]
                  }
              ],
          })),
          retcode=1) +
      api.post_process(has_log, 'test', 'Test.One (status FAILURE)') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('flake') +
      api.override_step_data(
          'test',
          api.test_utils.gtest_results(json.dumps({
              'per_iteration_data': [
                  {
                      'Test.One': [
                          {
                              'elapsed_time_ms': 0,
                              'output_snippet': ':(',
                              'status': 'FAILURE',
                          },
                          {
                              'elapsed_time_ms': 0,
                              'output_snippet': ':)',
                              'status': 'SUCCESS',
                          },
                      ]
                  }
              ],
          })),
          retcode=1) +
      api.post_process(doesnt_have_log, 'test', 'Test.One (status FAILURE)') +
      api.post_process(post_process.DropExpectation)
  )

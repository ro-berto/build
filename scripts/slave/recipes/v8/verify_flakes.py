# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to verify flaky tests (aka progression testing).

The recipe reads flake config and for each entry triggers flako recipe in
reproduce_only mode. If any flake fails to reproduce, the build is marked as
failed, which can then be used to alert sheriffs via a gatekeeper rule.
"""

import ast

from recipe_engine.post_process import (
    DropExpectation, MustRun, ResultReasonRE, StatusException, StatusFailure,
    StatusSuccess)


DEPS = [
    'depot_tools/gitiles',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/step',
]

MAX_CONFIGS = 16


def RunSteps(api):
  configs = ast.literal_eval(api.gitiles.download_file(
      'https://chromium.googlesource.com/v8/v8', 'flakes/flakes.pyl',
      branch='infra/config', step_name='read flake config'))
  if not configs:
    api.step('No flakes to reproduce', cmd=None)
    return

  if len(configs) > MAX_CONFIGS:
    too_many_flakes = api.step('Too many flake configs', cmd=None)
    too_many_flakes.presentation.status = api.step.FAILURE
    too_many_flakes.step_text = 'Running on first %d configs only' % MAX_CONFIGS
    configs = configs[:MAX_CONFIGS]

  v8_commits, _ = api.gitiles.log(
      'https://chromium.googlesource.com/v8/v8/', 'master', limit=1,
      step_name='read V8 ToT revision')
  v8_tot = v8_commits[0]['commit']
  put_result = api.buildbucket.put(
      (
        {
          'bucket': 'luci.v8.try',
          'parameters': {
            'builder_name': 'v8_flako',
            'properties': dict(
              flako_properties,
              repro_only=True,
              swarming_priority=40,
              to_revision=v8_tot,
              max_calibration_attempts=1,
            ),
          },
        } for flako_properties in configs
      ),
      name='trigger flako builds',
  )

  results = [
    api.buildbucket.collect_build(
      int(build['build']['id']), step_name='build #%d' % index,
      mirror_status=True, timeout=4*3600).status
    for index, build in enumerate(put_result.stdout['results'], start=1)
  ]

  if api.buildbucket.common_pb2.INFRA_FAILURE in results:
    raise api.step.InfraFailure('Some builds failed to execute')
  elif api.buildbucket.common_pb2.FAILURE in results:
    raise api.step.StepFailure('Some flakes failed to reproduce')
  else:
    api.step('All flakes still reproduce', cmd=None)


def GenTests(api):
  def test(name, results):
    return (
        api.test(name) +
        api.step_data(
            'read flake config',
            api.gitiles.make_encoded_file("[{'foo': 'bar',},]")) +
        api.step_data(
            'read V8 ToT revision',
            api.gitiles.make_log_test_data('deadbeef')) +
        api.override_step_data(
            'trigger flako builds',
            api.json.output_stream({'results': [{'build': {'id': "123"}}]})) +
        api.buildbucket.simulated_collect_output(
            [api.buildbucket.ci_build_message(build_id=123, status=result)
             for result in results],
            step_name='build #1')
    )

  yield (
      test('success', ['SUCCESS']) +
      api.post_process(StatusSuccess)
  )

  yield (
      test('failure', ['FAILURE']) +
      api.post_process(StatusFailure) +
      api.post_process(ResultReasonRE, 'Some flakes failed to reproduce') +
      api.post_process(DropExpectation)
  )

  yield (
      test('infra_failure', ['INFRA_FAILURE']) +
      api.post_process(StatusException) +
      api.post_process(ResultReasonRE, 'Some builds failed to execute') +
      api.post_process(DropExpectation)
  )

  yield (
      api.test('no_flakes') +
      api.step_data('read flake config', api.gitiles.make_encoded_file('[]')) +
      api.post_process(MustRun, 'No flakes to reproduce') +
      api.post_process(StatusSuccess) +
      api.post_process(DropExpectation)
  )

  yield (
      test('too_many_flakes', ['SUCCESS'] * 20) +
      api.override_step_data(
          'read flake config',
          api.gitiles.make_encoded_file(api.json.dumps(
            [{'foo': 'bar'}] * 20))) +
      api.post_process(MustRun, 'Too many flake configs') +
      api.post_process(DropExpectation)
  )

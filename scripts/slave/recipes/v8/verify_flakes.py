# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Recipe to verify flaky tests (aka progression testing).

The recipe reads flake config and for each entry triggers flako recipe in
reproduce_only mode. If any flake fails to reproduce, the build is marked as
failed, which can then be used to alert sheriffs via a gatekeeper rule.
"""

import ast
import re

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.buildbucket.proto import rpc as rpc_pb2

from recipe_engine.post_process import (
    DropExpectation, MustRun, ResultReasonRE, StatusException, StatusFailure,
    StatusSuccess, Filter)


DEPS = [
    'depot_tools/gitiles',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/step',
    'v8',
]

MAX_CONFIGS = 16
URL_FORMAT_RE = re.compile(r'(?:https?://)?(.+)')

TEST_CONFIG = [{
  'bisect_buildername': 'V8 Linux64 - debug builder',
  'bisect_mastername': 'client.v8',
  'bug_url': 'https://crbug.com/v8/8744',
  'build_config': 'Debug',
  'extra_args': [],
  'isolated_name': 'bot_default',
  'num_shards': 2,
  'repetitions': 5000,
  'swarming_dimensions': [
    'cpu:x86-64-avx2',
    'gpu:none',
    'os:Ubuntu-14.04',
    'pool:Chrome'
  ],
  'test_name': 'cctest/test-cpu-profiler/FunctionCallSample',
  'timeout_sec': 60,
  'total_timeout_sec': 120,
  'variant': 'interpreted_regexp'
}]


def update_step_presentation(api, presentation, build, flake_config):
  presentation.links['build %s' % build.id] = (
      api.buildbucket.build_url(build_id=build.id))
  bug_url = flake_config.get('bug_url')
  if bug_url:
    presentation.links[URL_FORMAT_RE.match(bug_url).group(1)] = bug_url
  presentation.logs['flake config'] = api.json.dumps(
      flake_config, indent=2).splitlines()
  if build.status == common_pb2.FAILURE:
    presentation.step_text = (
        'failed to reproduce<br/>please consider re-enabling this test')
  elif build.status == common_pb2.SUCCESS:
    presentation.step_text = 'reproduced'
  else:
    presentation.step_text = 'failed to execute'


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
      'https://chromium.googlesource.com/v8/v8/', 'refs/heads/master', limit=1,
      step_name='read V8 ToT revision')
  v8_tot = v8_commits[0]['commit']
  builds = api.v8.buildbucket_trigger([
    (
      'v8_flako',
      dict(
        flako_properties,
        repro_only=True,
        swarming_priority=40,
        to_revision=v8_tot,
        max_calibration_attempts=1,
      )
    ) for flako_properties in configs
  ], step_name='trigger flako builds')
  api.buildbucket.set_output_gitiles_commit(common_pb2.GitilesCommit(
      host='chromium.googlesource.com', project='v8/v8',
      ref='refs/heads/master', id=v8_tot))

  non_flaky_tests = []
  for index, build in enumerate(builds):
    label = api.v8.ui_test_label(configs[index]['test_name'])
    build = api.buildbucket.collect_build(
        int(build.id), step_name=label, mirror_status=True, timeout=4*3600)
    update_step_presentation(
        api, api.step.active_result.presentation, build, configs[index])
    if build.status == common_pb2.FAILURE:
      non_flaky_tests.append(label)

  if non_flaky_tests:
    raise api.step.StepFailure(
        'Some flakes failed to reproduce: %s' % ', '.join(non_flaky_tests))
  else:
    api.step('No flakes that fail to reproduce', cmd=None)


def GenTests(api):
  def test(name, results, ui_test_name=None):
    return (
        api.test(name) +
        api.step_data(
            'read flake config',
            api.gitiles.make_encoded_file(api.json.dumps(TEST_CONFIG))) +
        api.step_data(
            'read V8 ToT revision',
            api.gitiles.make_log_test_data('deadbeef')) +
        api.buildbucket.simulated_schedule_output(
            rpc_pb2.BatchResponse(
                responses=[dict(schedule_build=dict(id=123))],
            ),
            step_name='trigger flako builds') +
        api.buildbucket.simulated_collect_output(
            [api.buildbucket.ci_build_message(build_id=123, status=result)
             for result in results],
            step_name=ui_test_name or 'FunctionCallSample')
    )

  yield (
      test('success', ['SUCCESS']) +
      api.post_process(StatusSuccess)
  )

  yield (
      test('failure', ['FAILURE']) +
      api.post_process(StatusFailure) +
      api.post_process(
        ResultReasonRE, 'Some flakes failed to reproduce: FunctionCallSample') +
      api.post_process(DropExpectation)
  )

  yield (
      test('infra_failure', ['INFRA_FAILURE']) +
      api.post_process(StatusSuccess) +
      api.post_process(Filter('FunctionCallSample'))
  )

  yield (
      api.test('no_flakes') +
      api.step_data('read flake config', api.gitiles.make_encoded_file('[]')) +
      api.post_process(MustRun, 'No flakes to reproduce') +
      api.post_process(StatusSuccess) +
      api.post_process(DropExpectation)
  )

  yield (
      test('too_many_flakes', ['SUCCESS'] * 20, ui_test_name='baz') +
      api.override_step_data(
          'read flake config',
          api.gitiles.make_encoded_file(api.json.dumps(
            [{'test_name': 'foo/bar/baz'}] * 20))) +
      api.post_process(MustRun, 'Too many flake configs') +
      api.post_process(DropExpectation)
  )

# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

import PB.go.chromium.org.foundry_x.re_client.api.stats.stats as stats_pb

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'reclient',
]

_NINJA_STEP_NAME = 'compile (reclient)'


def RunSteps(api):
  api.path['checkout'] = api.path['tmp_base'].join('checkout')
  ninja_command = ['ninja', '-C', 'out/Release']
  with api.reclient.process(
      ninja_step_name=_NINJA_STEP_NAME, ninja_command=ninja_command):
    api.step(_NINJA_STEP_NAME, ninja_command)
  _ = api.reclient.instance  # for code coverage
  _ = api.reclient.rewrapper_path
  _ = api.reclient.metrics_project
  _ = api.reclient.jobs


def MakeTestRBEStats(num_records=0, total_verified=None, total_mismatches=None):
  stats = stats_pb.Stats(num_records=num_records)
  if total_verified is not None:
    stats.stats.add(
        name='LocalMetadata.Verification.TotalVerified', count=total_verified)
  if total_mismatches is not None:
    stats.verification.total_mismatches = total_mismatches
  return stats.SerializeToString()


def GenTests(api):
  yield (api.test('basic'))
  yield (api.test('basic windows') + api.platform('win', 64))
  yield (api.test('override instance') +
         api.reclient.properties(instance='goma') +
         api.post_process(post_process.DropExpectation))
  yield (api.test('override_metrics_project') +
         api.reclient.properties(metrics_project='goma'))

  def env_checker(check, steps):
    env = steps[_NINJA_STEP_NAME].env
    check(env['RBE_FOO'] == 'foo')
    check(env['RBE_BAR'] == 'bar')

  yield (api.test('proper_rewrapper_flags') +
         api.reclient.properties(rewrapper_env={
             'RBE_FOO': 'foo',
             'RBE_BAR': 'bar'
         }) + api.post_check(env_checker))
  yield (api.test('incorrect_rewrapper_flags') +
         api.reclient.properties(rewrapper_env={
             'MISSING_RBE_PREFIX': 'foo',
         }) + api.expect_exception('MalformedREWrapperFlag') +
         api.post_process(post_process.DropExpectation))

  yield (api.test('profiler') +
         api.reclient.properties(profiler_service='reclient') +
         api.post_process(
             post_process.Filter(
                 'preprocess for reclient.start reproxy via bootstrap')))

  yield (api.test('trace') + api.reclient.properties(publish_trace=True) +
         api.post_process(
             post_process.Filter(
                 'postprocess for reclient.upload reclient traces')))

  yield (api.test('ensure_verified_succeed') +
         api.reclient.properties(ensure_verified=True) + api.step_data(
             'postprocess for reclient.load rbe_metrics.pb',
             api.file.read_raw(
                 content=MakeTestRBEStats(num_records=1, total_verified=1))) +
         api.post_process(post_process.StepSuccess,
                          'postprocess for reclient.verification') +
         api.post_process(
             post_process.Filter('postprocess for reclient.verification')))

  yield (api.test('ensure_verified_no_records') +
         api.reclient.properties(ensure_verified=True) + api.step_data(
             'postprocess for reclient.load rbe_metrics.pb',
             api.file.read_raw(content=MakeTestRBEStats(num_records=0))) +
         api.post_process(post_process.StepSuccess,
                          'postprocess for reclient.verification') +
         api.post_process(
             post_process.Filter('postprocess for reclient.verification')))

  yield (api.test('ensure_verified_no_verified_field') +
         api.reclient.properties(ensure_verified=True) + api.step_data(
             'postprocess for reclient.load rbe_metrics.pb',
             api.file.read_raw(content=MakeTestRBEStats(num_records=1))) +
         api.post_process(post_process.StepException,
                          'postprocess for reclient.verification') +
         api.post_process(
             post_process.Filter('postprocess for reclient.verification')))

  yield (api.test('ensure_verified_no_verification') +
         api.reclient.properties(ensure_verified=True) + api.step_data(
             'postprocess for reclient.load rbe_metrics.pb',
             api.file.read_raw(
                 content=MakeTestRBEStats(num_records=1, total_verified=0))) +
         api.post_process(post_process.StepException,
                          'postprocess for reclient.verification') +
         api.post_process(
             post_process.Filter('postprocess for reclient.verification')))

  yield (api.test('ensure_verified_mismatches') +
         api.reclient.properties(ensure_verified=True) + api.step_data(
             'postprocess for reclient.load rbe_metrics.pb',
             api.file.read_raw(
                 content=MakeTestRBEStats(
                     num_records=1, total_verified=1, total_mismatches=1))) +
         api.post_process(post_process.StepException,
                          'postprocess for reclient.verification') +
         api.post_process(
             post_process.Filter('postprocess for reclient.verification')))

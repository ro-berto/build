# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'recipe_engine/context',
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

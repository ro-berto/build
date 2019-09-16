# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_android',
    'chromium_checkout',
    'chromium_tests',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')
  api.chromium.set_config('chromium', TARGET_PLATFORM='android')
  api.chromium_android.set_config('main_builder')
  api.chromium_checkout.ensure_checkout({})

  test = api.chromium_tests.steps.AndroidJunitTest(
      'test_name', target_name=api.properties.get('target_name'))

  try:
    test.run(api.chromium_tests.m, '')
  finally:
    assert test.has_valid_results('')
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(),
        'failures: %r' % test.failures(''),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):

  def calls_runner_script(check, step_odict, step, runner_script_name):
    runner_script = step_odict[step].cmd[0]
    check('step %s called runner script %s' % (step, runner_script_name),
          runner_script.endswith('bin/%s' % runner_script_name))

  yield api.test(
      'basic',
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123), api.properties(mastername='test_mastername'),
      api.post_process(post_process.MustRun, 'test_name'),
      api.post_process(calls_runner_script, 'test_name', 'run_test_name'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'different-target-name',
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123),
      api.properties(mastername='test_mastername', target_name='target_name'),
      api.post_process(post_process.MustRun, 'test_name'),
      api.post_process(calls_runner_script, 'test_name', 'run_target_name'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation))

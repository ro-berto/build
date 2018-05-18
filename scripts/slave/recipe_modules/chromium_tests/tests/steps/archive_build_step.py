# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/properties',
    'recipe_engine/runtime',
    'recipe_engine/step',
]

from recipe_engine import post_process


def RunSteps(api):
  api.chromium.set_config('chromium')

  test = api.chromium_tests.steps.ArchiveBuildStep('test-bucket')

  try:
    test.run(api, '')
  finally:
    api.step('details', [])
    api.step.active_result.presentation.logs['details'] = [
        'compile_targets: %r' % test.compile_targets(api),
        'uses_local_devices: %r' % test.uses_local_devices,
    ]


def GenTests(api):

  def verify_bucket_path(check, step_odict, expected_path):
    path = ''
    step = step_odict['archive build']
    check('cmd' in step)
    for cmd in step['cmd']:
      try:
        cmd = json.loads(cmd)
        if isinstance(cmd, dict) and 'gs_bucket' in cmd:
          path = cmd['gs_bucket']
          break
      except ValueError:
        pass
    check(path == expected_path)
    return step_odict

  yield (
      api.test('basic') +
      api.properties(
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123) +
      api.runtime(is_luci=False, is_experimental=False) +
      api.post_process(post_process.MustRun, 'archive build') +
      api.post_process(verify_bucket_path, 'gs://test-bucket') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('LUCI_experimental') +
      api.properties(
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123) +
      api.runtime(is_luci=True, is_experimental=True) +
      api.post_process(post_process.MustRun, 'archive build') +
      api.post_process(verify_bucket_path, 'gs://test-bucket/experimental') +
      api.post_process(post_process.DropExpectation)
  )

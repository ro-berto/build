# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests a recipe CL by running a chromium builder."""

from recipe_engine import post_process

DEPS = [
    'recipe_engine/context',
    'recipe_engine/led',
    'recipe_engine/properties',
    'recipe_engine/step',
]

SCHEDULING_TIMEOUT_SEC = 3600


def RunSteps(api):
  # Clear out SWARMING_TASK_ID in the environment so that the created tasks
  # do not have a parent task ID. This allows the triggered tasks to outlive
  # the current task instead of being cancelled when the current task
  # completes.
  # TODO(https://crbug.com/1140621) Use command-line option instead of
  # changing environment.
  with api.context(env={'SWARMING_TASK_ID': None}):
    builder = api.properties['builder_to_warm']

    with api.step.nest('get ' + builder):
      led_builder = api.led('get-builder',
                            'luci.chromium.try:{}'.format(builder))
      led_builder = led_builder.then('edit', '-name',
                                     'led: warm {}'.format(builder))
      led_builder.result.buildbucket.bbagent_args.build.scheduling_timeout \
          .FromSeconds(SCHEDULING_TIMEOUT_SEC)

    led_builder.then('launch')


def GenTests(api):
  yield api.test('basic', api.properties(builder_to_warm='linux_warmed'))

  yield api.test(
      'non_existent_builder',
      api.properties(builder_to_warm='non_existent_builder'),
      api.led.mock_get_builder(None),
      api.post_check(post_process.StepFailure,
                     'get non_existent_builder.led get-builder'))

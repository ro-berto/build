# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'swarming',
  'recipe_engine/platform',
  'recipe_engine/properties',
]

from recipe_engine import post_process


def RunSteps(api):
  opt_dims = {60: [{'os': 'Ubuntu-14.04'}]}
  task = api.swarming.task(
      api.properties.get('task_name', 'sample_task'),
      '0123456789012345678901234567890123456789',
      optional_dimensions=opt_dims)
  task.dimensions['os'] = api.swarming.prefered_os_dimension(
      api.platform.name)
  if api.properties.get('wait_for_capacity'):
    task.wait_for_capacity = True
  api.swarming.trigger_task(task)
  api.swarming.collect_task(task)


def GenTests(api):

  yield (
    api.test('wait_for_capacity') +
    api.properties(
        task_name='capacity-constrained task',
        wait_for_capacity=True) +
    api.post_process(
        post_process.StepCommandContains,
        '[trigger] capacity-constrained task',
        ['--wait-for-capacity']) +
    api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('optional_dimensions') +
    api.properties(
        task_name='optional-dimension task',
        wait_for_capacity=True) +
    api.post_process(
        post_process.StepCommandContains,
        '[trigger] optional-dimension task',
        ['--optional-dimension', 'os', 'Ubuntu-14.04', '60']) +
    api.post_process(post_process.DropExpectation)
  )

# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium_swarming',
  'recipe_engine/platform',
  'recipe_engine/properties',
]

from recipe_engine import recipe_test_api, post_process


def RunSteps(api):
  opt_dims = {60: [{'os': 'Ubuntu-14.04'}]}
  task = api.chromium_swarming.task(
      name=api.properties.get('task_name', 'sample_task'),
      isolated='0123456789012345678901234567890123456789',
      optional_dimensions=opt_dims,
      env_prefixes={'FOO': ['some/path']})
  if api.properties.get('wait_for_capacity'):
    task.wait_for_capacity = True

  task_slice = task.request[0]
  task_dimensions = task_slice.dimensions
  task_dimensions['os'] = api.chromium_swarming.prefered_os_dimension(
      api.platform.name)
  task_dimensions['pool'] = api.properties.get('pool', 'chromium.tests')
  task_slice = task_slice.with_dimensions(**task_dimensions)
  task.request = task.request.with_slice(0, task_slice)

  if api.properties.get('containment_type'):
    task.containment_type = api.properties['containment_type']
  api.chromium_swarming.trigger_task(task)
  kwargs = {}
  if api.properties.get('allow_missing_json'):
    kwargs['allow_missing_json'] = True
  api.chromium_swarming.collect_task(task, **kwargs)


def GenTests(api):

  yield api.test(
      'wait_for_capacity',
      api.properties(
          task_name='capacity-constrained task', wait_for_capacity=True),
      api.post_process(post_process.StepCommandContains,
                       '[trigger] capacity-constrained task',
                       ['--wait-for-capacity']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'containment_type',
      api.properties(task_name='windows gpu task', containment_type='AUTO'),
      api.post_process(post_process.StepCommandContains,
                       '[trigger] windows gpu task',
                       ['--containment-type', 'AUTO']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'optional_dimensions',
      api.properties(
          task_name='optional-dimension task', wait_for_capacity=True),
      api.post_process(post_process.StepCommandContains,
                       '[trigger] optional-dimension task',
                       ['--optional-dimension', 'os', 'Ubuntu-14.04', '60']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'allow_missing_json',
      api.properties(
          task_name='missing-json task', allow_missing_json=True),
      api.post_process(post_process.StepCommandContains,
                       'missing-json task',
                       ['--allow-missing-json']),
      api.post_process(post_process.DropExpectation),
  )

  def bad_summary_json():
    step_test_data = recipe_test_api.StepTestData()
    key = ('chromium_swarming', 'summary', None)
    placeholder = recipe_test_api.PlaceholderTestData('bad JSON')
    step_test_data.placeholder_data[key] = placeholder
    return step_test_data

  yield api.test(
      'bad-summary',
      api.properties(task_name='task'),
      api.step_data('task', bad_summary_json()),
      api.post_check(post_process.StepException, 'task'),
      api.post_check(post_process.StepTextContains, 'task',
                     ['Missing or invalid summary']),
      api.post_process(post_process.DropExpectation),
  )

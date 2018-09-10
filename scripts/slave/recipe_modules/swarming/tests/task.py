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
  task = api.swarming.task(
      api.properties.get('task_name', 'sample_task'),
      '0123456789012345678901234567890123456789')
  task.dimensions['os'] = api.swarming.prefered_os_dimension(
      api.platform.name)
  if api.properties.get('wait_for_capacity'):
    task.wait_for_capacity = True
  api.swarming.trigger_task(task)
  api.swarming.collect_task(task)


def GenTests(api):

  # TODO(jbudorick): Remove this after upstreaming it into post_process.
  def command_line_contains(check, step_odict, step_name, argument_sequence):
    def subsequence(containing, contained):
      for i in xrange(len(containing) - len(contained)):
        if containing[i:i+len(contained)] == contained:
          return True
      return False  # pragma: no cover

    check('No step named "%s"' % step_name,
          step_name in step_odict)
    check('Command line for step "%s" did not contain "%s"' % (
              step_name, ' '.join(argument_sequence)),
          subsequence(step_odict[step_name]['cmd'], argument_sequence))
    return step_odict

  yield (
    api.test('wait_for_capacity') +
    api.properties(
        task_name='capacity-constrained task',
        wait_for_capacity=True) +
    api.post_process(
        command_line_contains,
        step_name='[trigger] capacity-constrained task',
        argument_sequence=['--wait-for-capacity']) +
    api.post_process(post_process.DropExpectation)
  )

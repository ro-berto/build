#!/usr/bin/env vpython
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import sys
import tempfile
import unittest

import mock

THIS_DIR = os.path.dirname(__file__)

sys.path.insert(
    0, os.path.abspath(os.path.join(THIS_DIR, '..', 'resources')))
import wait_for_finished_task_set

class TasksToCollectTest(unittest.TestCase):
  def test_swarming_url(self):
    tasks = wait_for_finished_task_set.TasksToCollect([[]])
    self.assertEquals(tasks.swarming_query_url([]), 'tasks/get_states?')
    # Directly assign to the attribute to bypass the property calculation.
    # Add an unsorted array to make sure the url itself gets sorted.
    tasks = wait_for_finished_task_set.TasksToCollect([['b', 'a', 'c']])
    self.assertEquals(
        tasks.swarming_query_url(['a', 'b', 'c']),
        'tasks/get_states?task_id=a&task_id=b&task_id=c')

  def test_empty(self):
    tasks = wait_for_finished_task_set.TasksToCollect([[]])
    self.assertEquals(tasks.unfinished_tasks, [])
    self.assertEquals(tasks.finished_task_sets, [])

  def test_one_set(self):
    tasks = wait_for_finished_task_set.TasksToCollect([['a', 'b', 'c']])
    self.assertEquals(tasks.unfinished_tasks, ['a', 'b', 'c'])
    self.assertEquals(tasks.finished_task_sets, [])

    tasks.process_result({
        'states': ['PENDING', 'PENDING', 'COMPLETED']
    }, 3)
    self.assertEquals(tasks.unfinished_tasks, ['a', 'b'])
    self.assertEquals(tasks.finished_task_sets, [])

    tasks.process_result({
        'states': ['COMPLETED', 'COMPLETED']
    }, 2)
    self.assertEquals(tasks.unfinished_tasks, [])
    self.assertEquals(tasks.finished_task_sets, [['a', 'b', 'c']])

  def test_many_tasks(self):
    with mock.patch('wait_for_finished_task_set.TASK_BATCH_SIZE', 4):
      tasks = wait_for_finished_task_set.TasksToCollect([[
          str(i) + 'task' for i in range(11)]])
      self.assertEquals(
          tasks.task_batches,
          # 10task is in the first list because the list of tasks is sorted.
          [['0task', '10task', '1task', '2task'],
           ['3task', '4task', '5task', '6task'],
           ['7task', '8task', '9task']])

  def test_multiple_sets(self):
    tasks = wait_for_finished_task_set.TasksToCollect([
        ['a', 'b', 'c'],
        ['d'],
        ['e', 'f'],
    ])

    self.assertEquals(tasks.unfinished_tasks, ['a', 'b', 'c', 'd', 'e', 'f'])
    self.assertEquals(tasks.finished_task_sets, [])

    tasks.process_result({
        'states': [
            # Set 1
            'PENDING', 'COMPLETED', 'PENDING',
            # Set 2
            'COMPLETED',
            # Set 3
            'PENDING', 'RUNNING'
        ]
    }, 6)
    self.assertEquals(tasks.unfinished_tasks, ['a', 'c', 'e', 'f'])
    self.assertEquals(tasks.finished_task_sets, [['d']])

    tasks.process_result({
        'states': [
            # Set 1
            'PENDING', 'COMPLETED',
            # Set 2
            'COMPLETED', 'COMPLETED',
        ]
    }, 4)
    self.assertEquals(tasks.unfinished_tasks, ['a'])
    self.assertEquals(tasks.finished_task_sets, [['d'], ['e', 'f']])

    tasks.process_result({
        'states': [
            'COMPLETED'
        ]
    }, 1)
    self.assertEquals(tasks.unfinished_tasks, [])
    self.assertEquals(tasks.finished_task_sets, [
        ['a', 'b', 'c'], ['d'], ['e', 'f']])

class WaitForFinishedTaskSetTest(unittest.TestCase):
  @mock.patch('wait_for_finished_task_set.real_main')
  def test_main(self, real_main):
    """Tests the real main, to make sure there aren't small syntax errors."""
    real_main.return_value = (127, None)
    fd, fname = tempfile.mkstemp()
    os.close(fd)
    try:
      with open(fname, 'w') as f:
        json.dump([['foo']], f)

      self.assertEqual(wait_for_finished_task_set.main([
          None,
          '--swarming-server', 'blah',
          '--swarming-py-path', '/path/to/swarming.py',
          '--output-json', '/path/to/out.json',
          '--input-json', fname,
      ]), 127)
    finally:
      if os.path.exists(fname):
        os.unlink(fname)

  @mock.patch('wait_for_finished_task_set.subprocess.call')
  @mock.patch('wait_for_finished_task_set.time.sleep')
  def test_integration(self, sleep_mock, call_mock):
    m = mock.mock_open(read_data=json.dumps({
        'states': ['COMPLETED', 'COMPLETED']
    }))
    with mock.patch('wait_for_finished_task_set.open', m):
      call_mock.return_value = 0
      retcode, out_json = wait_for_finished_task_set.real_main(
          wait_for_finished_task_set.TasksToCollect([
              ['a', 'b'],
          ]), 3, 'swarming-py-path', 'https://swarming-server', None)
      self.assertEquals(retcode, 0)
      self.assertEquals(out_json, {
          'attempts': 3,
          'sets': [['a', 'b']]
      })

    # Shouldn't ever be called, just here so that if it gets called accidentally
    # the tests don't take forever.
    sleep_mock.assert_not_called()

  @mock.patch('wait_for_finished_task_set.time.sleep')
  @mock.patch('wait_for_finished_task_set.subprocess.call')
  def test_integration_sleep(self, call_mock, sleep_mock):
    m = mock.mock_open(read_data=json.dumps({
        'states': ['COMPLETED', 'COMPLETED']
    }))
    with mock.patch('wait_for_finished_task_set.open', m):
      call_mock.side_effect = lambda *args: 0
      tasks = wait_for_finished_task_set.TasksToCollect([
          ['a', 'b'],
      ])
      tasks.process_result = mock.MagicMock()
      num_calls = [0]
      def side_effect(_, __):
        if num_calls[0] > 8:
          tasks.finished_tasks.add('a')
          tasks.finished_tasks.add('b')
        num_calls[0] += 1

      tasks.process_result.side_effect = side_effect

      retcode, out_json = wait_for_finished_task_set.real_main(
          tasks, 0, 'swarming-py-path', 'https://swarming-server', None)
      self.assertEquals(retcode, 0)
      self.assertEquals(out_json, {
          'attempts': 9,
          'sets': [['a', 'b']]
      })

    self.assertEquals(
        sleep_mock.mock_calls, [
            mock.call(2),
            mock.call(4),
            mock.call(8),
            mock.call(16),
            mock.call(32),
            mock.call(64),
            # Ensure the sleeping time is capped at 2 minutes.
            mock.call(120),
            mock.call(120),
            mock.call(120),
        ])

if __name__ == '__main__':
  unittest.main()

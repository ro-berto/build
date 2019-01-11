#!/usr/bin/env python
# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import time


# Did some testing, and it looks like the swarming server starts 400-ing when
# you request a URL which has about 320 task ids in it. Stay a bit under that to
# be safe.
TASK_BATCH_SIZE = 300

class TasksToCollect(object):
  @classmethod
  def read_from_file(cls, filename):
    with open(filename) as f:
      input_data = json.load(f)

    return TasksToCollect(input_data)

  def __init__(self, input_data):
    self.task_sets = input_data
    self.finished_tasks = set()

  @property
  def unfinished_tasks(self):
    """Which tasks are unfinished.

    Returns a flat list of task ids."""
    tasks = []
    for sublist in self.task_sets:
      for item in sublist:
        if item not in self.finished_tasks:
          tasks.append(item)

    return sorted(tasks)

  @property
  def finished_task_sets(self):
    """Which task sets are ready to be collected."""
    finished = []
    for task_ids in self.task_sets:
      if task_ids and all(task in self.finished_tasks for task in task_ids):
        finished.append(task_ids)

    return finished

  @property
  def task_batches(self):
    tasks = self.unfinished_tasks
    return [
        tasks[idx:idx+TASK_BATCH_SIZE]
        for idx in xrange(0, len(tasks), TASK_BATCH_SIZE)
    ]

  def swarming_query_url(self, task_batch):
    """The swarming URL needed to collect task states."""
    return 'tasks/get_states?' + '&'.join(
        'task_id=%s' % task for task in task_batch)

  def process_result(self, result, num_tasks):
    """Handles the result of getting swarming task task_sets."""
    assert len(result['states']) == num_tasks

    for task_id, state in zip(self.unfinished_tasks, result['states']):
      if state not in ('PENDING', 'RUNNING'):
        self.finished_tasks.add(task_id)


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('--swarming-server', required=True)
  parser.add_argument('--swarming-py-path', required=True)
  parser.add_argument('--auth-service-account-json')
  parser.add_argument('--verbose', action='store_true')
  parser.add_argument('--output-json', required=True,
                      help='Where to output information about the results of '
                      'running this script. Will have two keys: \'attempts\', '
                      'which is the number of times we polled the swarming '
                      'server, and \'sets\', which is a list of finished '
                      'swarming task sets.')
  parser.add_argument('--attempts', default=0, type=int,
                      help='Number of times this script has tried to get'
                      ' results from the swarming server. Used to keep state'
                      ' across runs to not reset the exponential backoff.')
  parser.add_argument('--input-json', required=True,
                      help='List of sets of tasks. Each set of tasks is assumed'
                      ' to all be shards of the same root task.')

  args = parser.parse_args(argv[1:])

  logging.basicConfig(level=logging.DEBUG if args.verbose else logging.ERROR)

  tasks = TasksToCollect.read_from_file(args.input_json)

  retcode, output_json = real_main(
      tasks, args.attempts, args.swarming_py_path, args.swarming_server,
      args.auth_service_account_json)

  if output_json:
    with open(args.output_json, 'w') as f:
      json.dump(output_json, f)

  return retcode

def real_main(tasks, attempts, swarming_py_path, swarming_server,
              auth_service_account_json):
  fd, tmpfile = tempfile.mkstemp()
  os.close(fd)

  try:
    while True:
      for task_batch in tasks.task_batches:
        url = tasks.swarming_query_url(task_batch)

        cmd = [
            sys.executable,
            swarming_py_path,
            'query',
            '-S', swarming_server,
            '--json=%s' % tmpfile
        ]
        if auth_service_account_json:
          cmd.extend([
              '--auth-service-account-json', auth_service_account_json])

        cmd.append(url)

        logging.info('get_states cmd: %s', ' '.join(cmd))
        get_states_result = subprocess.call(cmd)
        if get_states_result != 0:
          logging.warn(
              'get_states cmd had non-zero return code: %s', get_states_result)
          return 1, None

        with open(tmpfile) as f:
          tasks.process_result(json.load(f), len(task_batch))

      if tasks.finished_task_sets:
        break

      # Do exponential backoff.
      attempts += 1
      time_to_sleep_sec = 2 ** attempts
      # Cap the sleep time at 2 minutes. Waiting longer than that could start to
      # impact the actual cycle time of the builder; if we wait for 16 minutes,
      # and (potentially) the final task finished one minute into that sleep,
      # we'd waste 15 minutes of time just sitting there. Ideally this would be
      # interrupt driven.
      time_to_sleep_sec = min(time_to_sleep_sec, 2 * 60)
      logging.info('sleeping for %d seconds' % time_to_sleep_sec)
      time.sleep(time_to_sleep_sec)
  finally:
    if os.path.exists(tmpfile):
      os.unlink(tmpfile)

  return 0, {
      'sets': tasks.finished_task_sets,
      'attempts': attempts,
  }

if __name__ == '__main__':
  sys.exit(main(sys.argv))

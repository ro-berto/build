# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

class SwarmingTestApi(recipe_test_api.RecipeTestApi):

  @recipe_test_api.placeholder_step_data
  def summary(self, data):
    return self.m.json.output(data)

  def canned_summary_output_raw(
      self, shards=1, shard_index=None, failure=False, internal_failure=False):
    shard_indices = range(shards) if shard_index is None else [shard_index]
    return {
      'shards': [
        {
          'abandoned_ts': None,
          'bot_id': 'vm30',
          'completed_ts': '2014-09-25T01:43:11.123',
          'created_ts': '2014-09-25T01:41:00.123',
          'duration': 31.5,
          'failure': failure,
          'task_id': '148aa78d7aa%02d00' % i,
          'internal_failure': internal_failure,
          'modified_ts': '2014-09-25 01:42:00',
          'name': 'heartbeat-canary-2014-09-25_01:41:55-os=Windows',
          'output': 'Heart beat succeeded on win32.\n'
          'Foo',
          'outputs_ref': {
            'isolated': 'abc123',
            'isolatedserver': 'https://isolateserver.appspot.com',
            'namespace': 'default-gzip',
          },
          'started_ts': '2014-09-25T01:42:11.123',
          'state': 'COMPLETED',
        } for i in shard_indices
      ],
    }

  def canned_summary_output(
      self, shards=1, shard_index=None, failure=False, internal_failure=False):
    return self.summary(self.canned_summary_output_raw(
        shards, shard_index, failure, internal_failure))

  def merge_script_log_file(self, data):
    return self.m.raw_io.output(data)

  def wait_for_finished_task_set(self, states, suffix=None):
    res = None
    for i, (tasks, attempts) in enumerate(states):
      name = 'wait for tasks%s%s' % (
          suffix or '', '' if not i else ' (%d)' % (i + 1))
      data = self.step_data(
          name, self.m.json.output(data={'sets': tasks, 'attempts': attempts}))
      if not res:
        res = data
      else:
        res += data

    return res

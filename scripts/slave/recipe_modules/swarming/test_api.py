# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from . import state

class SwarmingTestApi(recipe_test_api.RecipeTestApi):

  @recipe_test_api.placeholder_step_data
  def summary(self, data):
    return self.m.json.output(data)

  def canned_summary_output_raw(
      self, shards=1, failure=False, internal_failure=False):
    return {
      'shards': [
        {
          'abandoned_ts': None,
          'bot_id': 'vm30',
          'completed_ts': '2014-09-25T01:43:11.123',
          'created_ts': '2014-09-25T01:41:00.123',
          'durations': [5.7 + 3*i, 31.5],
          'exit_codes': [0, 0],
          'failure': failure,
          'id': '148aa78d7aa%02d00' % i,
          'internal_failure': internal_failure,
          'isolated_out': {
            'isolated': 'abc123',
            'isolatedserver': 'https://isolateserver.appspot.com',
            'namespace': 'default-gzip',
            'view_url': 'blah',
          },
          'modified_ts': '2014-09-25 01:42:00',
          'name': 'heartbeat-canary-2014-09-25_01:41:55-os=Windows',
          'outputs': [
            'Heart beat succeeded on win32.\n',
            'Foo',
          ],
          'outputs_ref': {
            'view_url': 'blah',
          },
          'started_ts': '2014-09-25T01:42:11.123',
          'state': state.State.COMPLETED,
          'try_number': 1,
          'user': 'unknown',
        } for i in xrange(shards)
      ],
    }

  def canned_summary_output(
      self, shards=1, failure=False, internal_failure=False):
    return self.summary(
      self.canned_summary_output_raw( shards, failure, internal_failure))

  def merge_script_log_file(self, data):
    return self.m.raw_io.output(data)

  def get_states(self, states, suffix=None):
    res = None
    for i, s in enumerate(states):
      name = 'collect tasks%s%s' % (suffix or '', '' if not i else ' (%d)' % (i + 1))
      data = self.step_data(
          name, self.m.json.output(data={
              'states': s,
          }))
      if not res:
        res = data
      else:
        res += data

    return res

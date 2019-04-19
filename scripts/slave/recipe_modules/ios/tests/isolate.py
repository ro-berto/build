# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools

from recipe_engine import config
from recipe_engine import post_process
from recipe_engine import recipe_api

DEPS = [
  'ios',
  'recipe_engine/assertions',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
]

PROPERTIES = {
    # Ordered list of partial tasks to validate.
    # All items in each partial task are expected to be present in
    # the corresponding actual task, though as the name implies, the partial
    # task does not have to contain every detail of the actual task.
    'expected_partial_tasks': recipe_api.Property(kind=config.List(dict)),
}


def RunSteps(api, expected_partial_tasks):
  api.ios.read_build_config()
  tasks = api.ios.isolate()
  for task, expected_partial_task in itertools.izip(
      tasks, expected_partial_tasks):
    partial_task = {
        k: task.get(k)
        for k in expected_partial_task.iterkeys()
    }
    api.assertions.assertEqual(partial_task, expected_partial_task)


def GenTests(api):
  yield (
      api.test('builder_with_testers')
      + api.platform('mac', 64)
      + api.properties(
          buildername='ios-builder',
          buildnumber='456',
          mastername='chromium.fake',
          parent_buildername='ios-builder',
          parent_buildnumber='456',
          parent_got_revision='fake revision',
          path_config='kitchen',
          expected_partial_tasks=[
              {
                  'buildername': 'ios-tester',
                  'task_id': '0_0',
              },
              {
                  'buildername': 'ios-tester',
                  'task_id': '0_1',
              },
          ],
      )
      + api.runtime(is_experimental=False, is_luci=True)
      + api.ios.make_test_build_config({
          'xcode version': '6.1.1',
          'gn_args': [
            'is_debug=true',
            'target_cpu="x64"',
            'use_goma=true',
          ],
          'triggered bots': [
            'ios-tester',
          ],
      })
      + api.ios.make_test_build_configs_for_children([
          {
            'xcode version': '6.1.1',
            'tests': [
              {
                'app': 'fake test 1',
                'device type': 'fake device',
                'os': '12.1',
                'xctest': True,
                'shard size': 2,
              },
            ],
            'triggered by': 'ios-builder',
          }
      ])
      + api.post_process(post_process.StatusSuccess)
      + api.post_process(post_process.DropExpectation)
  )

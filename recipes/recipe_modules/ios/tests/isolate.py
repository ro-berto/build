# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import itertools

from recipe_engine import config
from recipe_engine import post_process
from recipe_engine import recipe_api

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'ios',
    'recipe_engine/assertions',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
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
  for task, expected_partial_task in zip(tasks, expected_partial_tasks):
    partial_task = {k: task.get(k) for k in expected_partial_task}
    api.assertions.assertEqual(partial_task, expected_partial_task)


def GenTests(api):
  yield api.test(
      'builder_with_testers',
      api.platform('mac', 64),
      api.chromium.ci_build(
          builder_group='chromium.fake',
          builder='ios-builder',
          build_number=456,
          parent_buildername='ios-builder',
      ),
      api.properties(
          parent_buildnumber='456',
          parent_got_revision='fake revision',
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
      ),
      api.ios.make_test_build_config({
          'xcode version': '6.1.1',
          'gn_args': [
              'is_debug=true',
              'target_cpu="x64"',
              'use_goma=true',
          ],
          'triggered bots': ['ios-tester',],
      }),
      api.ios.make_test_build_configs_for_children([{
          'xcode version': '6.1.1',
          'tests': [{
              'app': 'fake test 1',
              'device type': 'fake device',
              'os': '12.1',
              'xctest': True,
              'swarming tasks': 2
          },],
          'triggered by': 'ios-builder',
      }]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

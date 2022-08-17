# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from PB.recipes.build.flakiness.reproducer import InputProperties

PROPERTIES = InputProperties

DEPS = [
    'flaky_reproducer',
    'recipe_engine/step',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
]


def RunSteps(api, properties):
  if properties.config:
    api.flaky_reproducer.set_config(properties.config)
  return api.flaky_reproducer.run(
      task_id=properties.task_id,
      build_id=properties.build_id,
      test_name=properties.test_name,
      test_id=properties.test_id)


def GenTests(api):
  yield api.test(
      'cannot_retrieve_invocation',
      api.properties(
          build_id="build-id",
          test_name="MockUnitTests.FailTest",
          config="manual",
      ),
      api.resultdb.query({}),
      api.post_check(post_process.ResultReason, 'Cannot retrieve invocation.'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'must_have_task_id_or_build_id',
      api.properties(
          task_id=None,
          build_id=None,
          test_id="not-exists",
      ),
      api.post_check(post_process.ResultReason,
                     'Must specify task_id or build_id.'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'must_have_test_id_or_test_name',
      api.properties(
          task_id='some-task',
          test_id=None,
          test_name=None,
      ),
      api.post_check(post_process.ResultReason,
                     'Must specify test_name or test_id.'),
      api.post_process(post_process.DropExpectation),
  )

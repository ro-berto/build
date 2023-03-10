# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests import steps

DEPS = [
    'builder_group',
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/legacy_annotation',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium.set_build_properties({
      'got_webrtc_revision': 'webrtc_sha',
      'got_v8_revision': 'v8_sha',
      'got_revision': 'd3adv3ggie',
      'got_revision_cp': 'refs/heads/main@{#54321}',
  })

  test_runner = api.chromium_tests.create_test_runner(
      tests=[
          steps.LocalGTestTestSpec.create('base_unittests').get_test(
              api.chromium_tests)
      ],
      serialize_tests=api.properties.get('serialize_tests'),
      retry_failed_shards=api.properties.get('retry_failed_shards'))
  return test_runner()


def GenTests(api):
  yield api.test(
      'failure',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.builder_group.for_current('test_group'),
      api.properties(
          buildername='test_buildername', bot_id='test_bot_id',
          buildnumber=123),
      api.override_step_data(
          'base_unittests',
          api.legacy_annotation.failure_step,
          stderr=api.raw_io.output_text(
              'rdb-stream: included "invocations/test-inv" in "build-inv"')),
  )

  yield api.test(
      'serialize_tests',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.builder_group.for_current('test_group'),
      api.properties(
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          serialize_tests=True),
      api.override_step_data(
          'base_unittests',
          api.legacy_annotation.failure_step,
          stderr=api.raw_io.output_text(
              'rdb-stream: included "invocations/test-inv" in "build-inv"')),
  )
  yield api.test(
      'retry_failed_shards',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.builder_group.for_current('test_group'),
      api.properties(
          buildername='test_buildername',
          bot_id='test_bot_id',
          buildnumber=123,
          retry_failed_shards=True),
      api.override_step_data(
          'base_unittests',
          api.legacy_annotation.failure_step,
          stderr=api.raw_io.output_text(
              'rdb-stream: included "invocations/test-inv" in "build-inv"')),
  )

# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'adb',
    'build',
    'chromium',
    'chromium_android',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'depot_tools/bot_update',
    'depot_tools/gsutil',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'recipe_engine/runtime',
    'test_results',
    'test_utils',
]

from recipe_engine import post_process


def RunSteps(api):
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  with api.chromium.chromium_layout():
    return api.chromium_tests.main_waterfall_steps(builder_id, builder_config)


def GenTests(api):
  yield api.test(
      'dynamic_gtest',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [
                      'base_unittests',
                      {
                          'test': 'browser_tests',
                          'shard_index': 0,
                          'total_shards': 2
                      },
                      {
                          'test': 'content_unittests',
                          'name': 'renamed_content_unittests',
                          'use_xvfb': False,
                      },
                  ],
              },
          }),
  )

  yield api.test(
      'dynamic_swarmed_gtest',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux', builder='Linux Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'resultdb': {
                          'enable': True
                      },
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      }
                  },],
              },
          }),
  )

  yield api.test(
      'dynamic_swarmed_serialized_gtests',
      # The chromium.gpu.fyi bots use serialize_tests in order to reduce
      # load on the GPU bots in the Swarming pool.
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.gpu.fyi',
          builder='Linux FYI Release (NVIDIA)',
          parent_buildername='GPU FYI Linux Builder'),
      api.properties(
          swarm_hashes={
              'base_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
              'browser_tests': 'ffffffffffffffffffffffffffffff/size',
          }),
      api.chromium_tests.read_source_side_spec(
          'chromium.gpu.fyi',
          {
              'Linux FYI Release (NVIDIA)': {
                  'gtest_tests': [
                      {
                          'test': 'base_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders':
                                  True,
                              'dimension_sets': [
                                  {
                                      'gpu':
                                          '10de:104a',  # NVIDIA GeForce GT 610
                                      'os': 'Linux',
                                  },
                              ],
                          },
                      },
                      {
                          'test': 'browser_tests',
                          'swarming': {
                              'can_use_on_swarming_builders':
                                  True,
                              'dimension_sets': [
                                  {
                                      'gpu':
                                          '10de:104a',  # NVIDIA GeForce GT 610
                                      'os': 'Linux',
                                  },
                              ],
                          },
                      },
                  ],
              },
          }),
      # Make one of the tests fail to improve code coverage.
      api.override_step_data(
          'base_unittests on NVIDIA GPU on Linux',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False))),
  )

  yield api.test(
      'dynamic_swarmed_gtest_mac_gpu',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.mac',
          builder='Mac10.13 Tests',
          parent_buildername='Mac Builder',
      ),
      api.properties(swarm_hashes={
          'gl_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac',
          {
              'Mac10.13 Tests': {
                  'gtest_tests': [
                      {
                          'test': 'gl_tests',
                          'swarming': {
                              'can_use_on_swarming_builders':
                                  True,
                              'dimension_sets': [
                                  {
                                      'gpu': '8086:0a2e',  # Intel Iris
                                      'hidpi': '0',
                                      'os': 'Mac-10.10',
                                  },
                                  {
                                      'gpu':
                                          '10de:0fe9',  # NVIDIA GeForce GT750M
                                      'hidpi': '1',
                                      'os': 'Mac-10.13',
                                  },
                              ],
                          },
                      },
                  ],
              },
          }),
  )

  yield api.test(
      'dynamic_swarmed_gtest_override_compile_targets',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux', builder='Linux Builder'),
      api.properties(swarm_hashes={
          'tab_capture_end2end_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'test': 'tab_capture_end2end_tests',
                      'override_compile_targets':
                          ['tab_capture_end2end_tests_run'],
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                  },],
              },
          }),
  )

  yield api.test(
      'build_dynamic_isolated_script_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux', builder='Linux Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                  },],
              },
          }),
  )

  yield api.test(
      'dynamic_isolated_script_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name':
                          'telemetry_gpu_unittests',
                      'name':
                          'telemetry_gpu_unittests',
                      'args': ['--correct-common-arg'],
                      'precommit_args':
                          ['--SHOULD-NOT-BE-PRESENT-DURING-THE-RUN'],
                      'non_precommit_args': [
                          '--these-args-should-be-present',
                          '--test-machine-name=\"${buildername}\"',
                          '--build-revision=\"${got_revision}\"',
                      ],
                  },],
              },
          }),
  )

  yield api.test(
      'dynamic_local_isolated_script_test_with_failed_json_results',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.test_utils.canned_isolated_script_output(
              passing=False,
              is_win=False,
              swarming=False,
              isolated_script_passing=False,
              use_json_test_format=True),
          retcode=0),
  )

  yield api.test(
      'dynamic_local_isolated_script_test_with_unknown_json_results',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.test_utils.canned_isolated_script_output(
              passing=True,
              is_win=False,
              swarming=False,
              isolated_script_passing=True,
              use_json_test_format=True,
              unknown=True),
          retcode=0),
  )

  yield api.test(
      'dynamic_local_isolated_script_test_with_corrupt_json_results',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.test_utils.canned_isolated_script_output(
              passing=True,
              is_win=False,
              swarming=False,
              isolated_script_passing=True,
              use_json_test_format=True,
              corrupt=True),
          retcode=0),
  )

  yield api.test(
      'dynamic_local_isolated_script_test_with_passed_json_results',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.test_utils.canned_isolated_script_output(
              passing=True,
              is_win=False,
              swarming=False,
              isolated_script_passing=True,
              use_json_test_format=True),
          retcode=0),
  )

  yield api.test(
      'dynamic_local_isolated_script_test_with_custom_results_handler',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'results_handler': 'fake',
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.test_utils.canned_isolated_script_output(
              passing=False,
              is_win=False,
              swarming=False,
              isolated_script_passing=False,
              use_json_test_format=True),
          retcode=0),
  )

  yield api.test(
      'dynamic_isolated_script_test_harness_failure_zero_retcode',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.test_utils.canned_isolated_script_output(
              passing=False,
              is_win=False,
              swarming=False,
              isolated_script_passing=False,
              valid=False),
          retcode=0),
  )

  yield api.test(
      'dynamic_isolated_script_test_harness_failure_no_json',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests', api.json.output(None), retcode=-11),
  )

  yield api.test(
      'build_dynamic_isolated_script_test_compile_target_overriden',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux', builder='Linux Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name':
                          'telemetry_gpu_unittests',
                      'name':
                          'telemetry_gpu_unittests',
                      'override_compile_targets':
                          ['abc', 'telemetry_gpu_unittests_run'],
                  },],
              },
          }),
  )

  yield api.test(
      'build_dynamic_swarmed_isolated_script_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux', builder='Linux Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
  )

  yield api.test(
      'build_dynamic_swarmed_isolated_script_test_compile_target_overidden',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux', builder='Linux Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name':
                          'telemetry_gpu_unittests',
                      'name':
                          'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                      'override_compile_targets':
                          ['telemetry_gpu_unittests_run', 'a'],
                  },],
              },
          }),
  )

  yield api.test(
      'dynamic_swarmed_passed_isolated_script_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
  )

  yield api.test(
      'dynamic_swarmed_sharded_passed_isolated_script_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          build_number=1234,
          parent_buildername='Linux Builder',
          revision='a' * 40),
      api.properties(
          version='v23523',
          swarm_hashes={
              'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size'
          }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  use_json_test_format=True,
                  output_chartjson=True),
              shards=2),
          retcode=0),
  )

  yield api.test(
      'dynamic_swarmed_sharded_corrupt_json_isolated_script_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 3,
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
                  shards=3,
                  isolated_script_passing=True,
                  corrupt=True,
                  use_json_test_format=True,
                  output_chartjson=True),
              shards=3)),
  )

  yield api.test(
      'dynamic_swarmed_sharded_invalid_json_isolated_script_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 3,
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.json.output({'version': 2}))),
  )

  yield api.test(
      'dynamic_swarmed_sharded_failed_isolated_script_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  is_win=False,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=False,
                  use_json_test_format=True),
              shards=2,
              retcode=1)),
  )

  yield api.test(
      'dynamic_swarmed_sharded_isolated_script_test_missing_shard',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  is_win=False,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=False,
                  valid=True,
                  missing_shards=[1]),
              shards=2)),
  )

  yield api.test(
      'dynamic_swarmed_sharded_isolated_script_test_harness_failure',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  is_win=False,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=False,
                  valid=True,
                  empty_shards=[1]),
              shards=2)),
  )

  yield api.test(
      'dynamic_swarmed_sharded_isolated_chartjson_test_harness_failure',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  is_win=False,
                  swarming=True,
                  shards=4,
                  isolated_script_passing=False,
                  empty_shards=[1],
                  output_chartjson=True,
                  use_json_test_format=True),
              shards=2)),
  )

  yield api.test(
      'dynamic_swarmed_sharded_isolated_chartjson_test_disabled',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  output_chartjson=True,
                  benchmark_enabled=False,
                  use_json_test_format=True),
              shards=2,
              retcode=0)),
  )

  yield api.test(
      'dynamic_swarmed_sharded_isolated_chartjson_test_missing_all_shards',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  missing_shards=[1],
                  output_chartjson=True,
                  use_json_test_format=True),
              shards=2,
              retcode=1)),
      api.post_process(post_process.DoesNotRun,
                       'telemetry_gpu_unittests Dashboard Upload'),
      api.post_process(post_process.Filter('telemetry_gpu_unittests')),
  )

  yield api.test(
      'dynamic_swarmed_sharded_isolated_chartjson_test_missing_shard',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 2,
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
                  shards=2,
                  isolated_script_passing=True,
                  missing_shards=[1],
                  output_chartjson=True,
                  use_json_test_format=True),
              shards=2,
              retcode=1)),
  )

  yield api.test(
      'dynamic_swarmed_isolated_script_test_linux_gpu',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux',
          {
              'Linux Tests': {
                  'isolated_scripts': [
                      {
                          'isolate_name': 'telemetry_gpu_unittests',
                          'name': 'telemetry_gpu_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders':
                                  True,
                              'dimension_sets': [
                                  {
                                      'gpu':
                                          '10de:104a',  # NVIDIA GeForce GT 610
                                      'os': 'Linux',
                                  },
                              ],
                          },
                      },
                  ],
              },
          }),
  )

  yield api.test(
      'dynamic_swarmed_isolated_script_test_mac_gpu',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.mac',
          builder='Mac10.13 Tests',
          parent_buildername='Mac Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac',
          {
              'Mac10.13 Tests': {
                  'isolated_scripts': [
                      {
                          'isolate_name': 'telemetry_gpu_unittests',
                          'name': 'telemetry_gpu_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders':
                                  True,
                              'dimension_sets': [
                                  {
                                      'gpu': '8086:0a2e',  # Intel Iris
                                      'hidpi': '0',
                                      'os': 'Mac-10.10',
                                  },
                                  {
                                      'gpu':
                                          '10de:0fe9',  # NVIDIA GeForce GT750M
                                      'hidpi': '1',
                                      'os': 'Mac-10.13',
                                  },
                              ],
                          },
                      },
                  ],
              },
          }),
  )

  yield api.test(
      'dynamic_swarmed_isolated_script_test_win_gpu',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.win',
          builder='Win7 Tests (1)',
          parent_buildername='Win Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.win',
          {
              'Win7 Tests (1)': {
                  'isolated_scripts': [
                      {
                          'isolate_name': 'telemetry_gpu_unittests',
                          'name': 'telemetry_gpu_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders':
                                  True,
                              'dimension_sets': [
                                  {
                                      # NVIDIA GeForce GT 610
                                      'gpu': '10de:104a',
                                      'os': 'Windows',
                                  },
                                  {
                                      # AMD Radeon HD 6450
                                      'gpu': '1002:6779',
                                      'os': 'Windows',
                                  },
                                  {
                                      # VMWare SVGA II Adapter
                                      'gpu': '15ad:0405',
                                      'os': 'Windows',
                                  },
                              ],
                          },
                      },
                  ],
              },
          }),
  )

  yield api.test(
      'dynamic_swarmed_isolated_script_test_win_non_gpu',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.win',
          builder='Win7 Tests (1)',
          parent_buildername='Win Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'dimension_sets': [{
                              'os': 'Windows',
                          },],
                      },
                  },],
              },
          }),
  )

  yield api.test(
      'dynamic_swarmed_failed_isolated_script_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
                  isolated_script_passing=False,
                  valid=True)),
          retcode=255),
  )

  yield api.test(
      'dynamic_swarmed_passed_with_bad_retcode_isolated_script_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
                  isolated_script_passing=True,
                  valid=True)),
          retcode=255),
  )

  yield api.test(
      'dynamic_swarmed_passed_isolated_script_test_with_swarming_failure',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  is_win=False,
                  swarming=True,
                  swarming_internal_failure=True,
                  isolated_script_passing=True,
                  valid=True),
              internal_failure=True),
          retcode=255),
  )

  yield api.test(
      'dynamic_swarmed_passed_isolated_script_test'
      '_with_swarming_failure_invalid',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  is_win=False,
                  swarming=True,
                  swarming_internal_failure=True,
                  isolated_script_passing=True,
                  valid=False),
              internal_failure=True),
          retcode=255),
  )

  yield api.test(
      'dynamic_swarmed_isolated_script_test_failure_no_result_json',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.override_step_data(
          'telemetry_gpu_unittests',
          api.chromium_swarming.canned_summary_output(
              api.json.output({}), failure=True, retcode=1)),
  )

  yield api.test(
      'dynamic_junit_test',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.android',
          builder='android-marshmallow-arm64-rel'),
      api.chromium_tests.read_source_side_spec(
          'chromium.android', {
              'android-marshmallow-arm64-rel': {
                  'junit_tests': [{
                      'test': 'base_junit_tests',
                  },],
              },
          }),
  )

  yield api.test(
      'dynamic_gtest_on_builder',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux', builder='Linux Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [
                      'base_unittests',
                      {
                          'test': 'browser_tests',
                          'shard_index': 0,
                          'total_shards': 2
                      },
                  ],
              },
          }),
  )

  yield api.test(
      'dynamic_gtest_win',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.win',
          builder='Win7 Tests (1)',
          parent_buildername='Win Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.win', {
              'Win7 Tests (1)': {
                  'gtest_tests': [
                      'aura_unittests',
                      {
                          'test': 'browser_tests',
                          'shard_index': 0,
                          'total_shards': 2
                      },
                  ],
              },
          }),
  )

  # Tests switching on asan and swiching off lsan for sandbox tester.
  yield api.test(
      'dynamic_gtest_memory_asan_no_lsan',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.memory',
          builder='Linux ASan Tests (sandboxed)',
          parent_buildername='Linux ASan LSan Builder'),
      api.chromium_tests.read_source_side_spec('chromium.memory', {
          'Linux ASan Tests (sandboxed)': {
              'gtest_tests': ['browser_tests',],
          },
      }),
  )

  # Tests that the memory builder is using the correct compile targets.
  yield api.test(
      'dynamic_gtest_memory_builder',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.memory',
          builder='Linux ASan LSan Builder',
          parent_buildername=None,
          revision='a' * 40),
      # The builder should build 'browser_tests', because there exists a child
      # tester that uses that test.
      api.chromium_tests.read_source_side_spec('chromium.memory', {
          'Linux ASan Tests (sandboxed)': {
              'gtest_tests': ['browser_tests',],
          },
      }),
  )

  # Tests that the memory mac tester is using the correct test flags.
  yield api.test(
      'dynamic_gtest_memory_mac64',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.memory',
          builder='Mac ASan 64 Tests (1)',
          parent_buildername='Mac ASan 64 Builder'),
      api.chromium_tests.read_source_side_spec('chromium.memory', {
          'Mac ASan 64 Tests (1)': {
              'gtest_tests': ['browser_tests',],
          },
      }),
  )

  yield api.test(
      'tsan',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.memory',
          builder='Linux TSan Tests',
          parent_buildername='Linux TSan Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.memory', {
              'Linux TSan Tests': {
                  'compile_targets': ['base_unittests'],
                  'gtest_tests': ['base_unittests'],
              },
          }),
  )

  yield api.test(
      'msan',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.memory',
          builder='Linux MSan Tests',
          parent_buildername='Linux MSan Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.memory', {
              'Linux MSan Tests': {
                  'compile_targets': ['base_unittests'],
                  'gtest_tests': ['base_unittests'],
              },
          }),
  )

  yield api.test(
      'buildnumber_zero',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder',
          build_number=0),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [
                      'base_unittests',
                      {
                          'test': 'browser_tests',
                          'shard_index': 0,
                          'total_shards': 2
                      },
                  ],
              },
          }),
  )

  yield api.test(
      'one_failure_keeps_going_dynamic_tests',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [
                      'base_unittests',
                      {
                          'test': 'browser_tests',
                          'shard_index': 0,
                          'total_shards': 2
                      },
                  ],
              },
          }),
      api.override_step_data('base_unittests',
                             api.legacy_annotation.failure_step),
  )

  yield api.test(
      'dynamic_script_test_failure',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'scripts': [{
                      'name': 'test_script_with_broken_tests',
                      'script': 'test_script_with_broken_tests.py'
                  }]
              }
          }),
      api.override_step_data(
          'test_script_with_broken_tests',
          api.json.output({
              'valid': True,
              'failures': ['FailSuite.Test1', 'FlakySuite.TestA']
          })),
  )

  json_results = {
    'interrupted': False,
    'version': 3,
    'path_delimiter': '/',
    'seconds_since_epoch': 0,
    'tests': {},
    'num_failures_by_type': {},
    'links': {'custom_link': 'http://example.com'}
  }


  yield api.test(
      'gtest_custom_merge_script',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'browser_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                      'merge': {
                          'script': '//fake_merge_script.py',
                      },
                  },],
              },
          }),
      api.post_process(post_process.Filter('browser_tests')),
  )

  yield api.test(
      'gtest_bad_custom_merge_script',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'browser_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                      'merge': {
                          'script': 'fake_merge_script.py',
                      },
                  },],
              },
          }),
  )

  yield api.test(
      'isolated_script_test_custom_merge_script',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.step_data('fake_test', api.json.output(json_results)),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'fake_test',
                      'name': 'fake_test',
                      'merge': {
                          'script': '//fake_merge_script.py',
                      },
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                  },],
              },
          }),
      api.post_process(post_process.Filter('fake_test')),
  )

  yield api.test(
      'isolated_script_test_bad_custom_merge_script',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'fake_test',
                      'name': 'fake_test',
                      'merge': {
                          'script': 'bad_fake_merge_script.py',
                      },
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                  },],
              },
          }),
  )

  yield api.test(
      'isolated_script_test_custom_merge_script_with_args',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.step_data('fake_test', api.json.output(json_results)),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'fake_test',
                      'name': 'fake_test',
                      'merge': {
                          'script': '//fake_merge_script.py',
                          'args': [
                              '--foo',
                              'foo_value',
                          ],
                      },
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                  },],
              },
          }),
      api.post_process(post_process.Filter('fake_test')),
  )

  yield api.test(
      'isolated_script_test_custom_results_handler',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.step_data('fake_test', api.json.output(json_results)),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'fake_test',
                      'name': 'fake_test',
                      'results_handler': 'fake',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                  },],
              },
          }),
      api.post_process(post_process.Filter('fake_test')),
  )

  yield api.test(
      'isolated_script_test_invalid_results_handler',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(swarm_hashes={
          'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee/size',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'fake_test',
                      'name': 'fake_test',
                      'results_handler': 'unknown',
                  },],
              },
          }),
  )

  yield api.test(
      'webrtc_chromium_mac_tester',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.webrtc',
          builder='WebRTC Chromium Mac Tester',
          parent_buildername='WebRTC Chromium Mac Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.webrtc',
          {
              'WebRTC Chromium Mac Tester': {
                  'gtest_tests': [{
                      'args': [
                          '--gtest_filter=WebRtcWebcamBrowserTests*:'
                          'WebRtcStatsPerfBrowserTest.*:'
                          'WebRtcVideoDisplayPerfBrowserTests*:'
                          'WebRtcVideoHighBitrateBrowserTest*:'
                          'WebRtcVideoQualityBrowserTests*', '--run-manual',
                          '--ui-test-action-max-timeout=300000',
                          '--test-launcher-timeout=350000',
                          '--test-launcher-jobs=1', '--test-launcher-bot-mode',
                          '--test-launcher-print-test-stdio=always'
                      ],
                      'merge': {
                          'script':
                              '//testing/merge_scripts/standard_gtest_merge.py'
                      },
                      'annotate': 'graphing',
                      'perf_builder_name_alias': 'chromium-webrtc-rel-mac',
                      'perf_config': {
                          'a_default_rev': 'r_webrtc_git',
                          'r_webrtc_git': '${webrtc_got_rev}'
                      },
                      'swarming': {
                          'can_use_on_swarming_builders': False
                      },
                      'test': 'browser_tests',
                  }],
              },
          },
      ),
      api.post_process(post_process.MustRun, 'ensure_installed'),
      api.post_process(post_process.StepSuccess, 'browser_tests'),
      api.post_process(post_process.StepSuccess,
                       'Upload to test-results [browser_tests]'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'webrtc_chromium_mac_tester_failure',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.webrtc',
          builder='WebRTC Chromium Mac Tester',
          parent_buildername='WebRTC Chromium Mac Builder'),
      api.chromium_tests.read_source_side_spec(
          'chromium.webrtc',
          {
              'WebRTC Chromium Mac Tester': {
                  'gtest_tests': [{
                      'args': [
                          '--gtest_filter=WebRtcWebcamBrowserTests*:'
                          'WebRtcStatsPerfBrowserTest.*:'
                          'WebRtcVideoDisplayPerfBrowserTests*:'
                          'WebRtcVideoHighBitrateBrowserTest*:'
                          'WebRtcVideoQualityBrowserTests*', '--run-manual',
                          '--ui-test-action-max-timeout=300000',
                          '--test-launcher-timeout=350000',
                          '--test-launcher-jobs=1', '--test-launcher-bot-mode',
                          '--test-launcher-print-test-stdio=always'
                      ],
                      'merge': {
                          'script':
                              '//testing/merge_scripts/standard_gtest_merge.py'
                      },
                      'annotate': 'graphing',
                      'perf_builder_name_alias': 'chromium-webrtc-rel-mac',
                      'perf_config': {
                          'a_default_rev': 'r_webrtc_git',
                          'r_webrtc_git': '${webrtc_got_rev}'
                      },
                      'swarming': {
                          'can_use_on_swarming_builders': False
                      },
                      'test': 'browser_tests',
                  }],
              },
          },
      ),
      api.override_step_data('browser_tests',
                             api.legacy_annotation.failure_step),
      api.post_process(post_process.StepFailure, 'browser_tests'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

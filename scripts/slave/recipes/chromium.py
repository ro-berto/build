# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'adb',
  'bisect_tester',
  'build',
  'chromium',
  'chromium_android',
  'chromium_swarming',
  'chromium_tests',
  'commit_position',
  'depot_tools/bot_update',
  'depot_tools/gsutil',
  'isolate',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'recipe_engine/tempfile',
  'recipe_engine/runtime',
  'swarming',
  'test_results',
  'test_utils',
]

from recipe_engine import config_types
from recipe_engine import post_process

def ignore_undumpable(obj):  # pragma: no cover
  try:
    return config_types.json_fixup(obj)
  except TypeError:
    return None


def RunSteps(api):
  # build/tests/masters_recipes_tests.py needs to manipulate the BUILDERS
  # dict, so we provide an API to dump it here.
  if api.properties.get('dump_builders'):  # pragma: no cover
    api.file.write_text(
        'Dump BUILDERS dict', api.properties['dump_builders'],
        api.json.dumps(api.chromium_tests.builders, default=ignore_undumpable))
    return

  with api.chromium.chromium_layout():
    api.chromium_tests.main_waterfall_steps()


def GenTests(api):
  yield (
    api.test('dynamic_gtest') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
              'gtest_tests': [
                'base_unittests',
                {'test': 'browser_tests', 'shard_index': 0, 'total_shards': 2},
                {
                    'test': 'content_unittests',
                    'name': 'renamed_content_unittests',
                    'use_xvfb': False,
                },
              ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_swarmed_gtest') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'gtest_tests': [
                    {'test': 'browser_tests',
                     'swarming': {'can_use_on_swarming_builders': True}},
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_swarmed_serialized_gtests') +
    # The chromium.gpu.fyi bots use serialize_tests in order to reduce
    # load on the GPU bots in the Swarming pool.
    api.properties.generic(mastername='chromium.gpu.fyi',
                           buildername='Linux FYI Release (NVIDIA)',
                           parent_buildername='GPU FYI Linux Builder') +
    api.platform('linux', 64) +
    api.properties(swarm_hashes={
      'base_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
      'browser_tests': 'ffffffffffffffffffffffffffffff',
    }) +
    api.override_step_data(
        'read test spec (chromium.gpu.fyi.json)',
        api.json.output({
            'Linux FYI Release (NVIDIA)': {
                'gtest_tests': [
                    {
                        'test': 'base_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'dimension_sets': [
                                {
                                    'gpu': '10de:104a',  # NVIDIA GeForce GT 610
                                    'os': 'Linux',
                                },
                            ],
                        },
                    },
                    {
                        'test': 'browser_tests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'dimension_sets': [
                                {
                                    'gpu': '10de:104a',  # NVIDIA GeForce GT 610
                                    'os': 'Linux',
                                },
                            ],
                        },
                    },
                ],
            },
        })
    ) +
    # Make one of the tests fail to improve code coverage.
    api.override_step_data('base_unittests on NVIDIA GPU on Linux',
        api.swarming.canned_summary_output(failure=True) +
        api.test_utils.canned_gtest_output(False))
  )

  yield (
    api.test('dynamic_swarmed_gtest_mac_gpu') +
    api.properties.generic(mastername='chromium.mac',
                           buildername='Mac10.13 Tests',
                           parent_buildername='Mac Builder') +
    api.properties(swarm_hashes={
      'gl_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('mac', 64) +
    api.override_step_data(
        'read test spec (chromium.mac.json)',
        api.json.output({
            'Mac10.13 Tests': {
                'gtest_tests': [
                    {
                        'test': 'gl_tests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'dimension_sets': [
                                {
                                    'gpu': '8086:0a2e',  # Intel Iris
                                    'hidpi': '0',
                                    'os': 'Mac-10.10',
                                }, {
                                    'gpu': '10de:0fe9',  # NVIDIA GeForce GT750M
                                    'hidpi': '1',
                                    'os': 'Mac-10.13',
                                },
                            ],
                        },
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_swarmed_gtest_override_compile_targets') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.properties(swarm_hashes={
      'tab_capture_end2end_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'gtest_tests': [
                    {
                        'test': 'tab_capture_end2end_tests',
                        'override_compile_targets': [
                            'tab_capture_end2end_tests_run'
                        ],
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                        },
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('build_dynamic_isolated_script_test') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_isolated_script_test') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'args': ['--correct-common-arg'],
                        'precommit_args': [
                            '--SHOULD-NOT-BE-PRESENT-DURING-THE-RUN'
                        ],
                        'non_precommit_args': [
                            '--these-args-should-be-present',
                            '--test-machine-name=\"${buildername}\"',
                            '--build-revision=\"${got_revision}\"',
                        ],
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_local_isolated_script_test_with_failed_json_results') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                    },
                ],
            },
        })
    ) + api.override_step_data('telemetry_gpu_unittests',
            api.test_utils.canned_isolated_script_output(
                passing=False, is_win=False, swarming=False,
                isolated_script_passing=False,
                use_json_test_format=True),
            retcode=0)
  )

  yield (
    api.test('dynamic_local_isolated_script_test_with_unknown_json_results') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                    },
                ],
            },
        })
    ) + api.override_step_data('telemetry_gpu_unittests',
            api.test_utils.canned_isolated_script_output(
                passing=True, is_win=False, swarming=False,
                isolated_script_passing=True,
                use_json_test_format=True, unknown=True),
            retcode=0)
  )

  yield (
    api.test('dynamic_local_isolated_script_test_with_corrupt_json_results') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                    },
                ],
            },
        })
    ) + api.override_step_data('telemetry_gpu_unittests',
            api.test_utils.canned_isolated_script_output(
                passing=True, is_win=False, swarming=False,
                isolated_script_passing=True,
                use_json_test_format=True, corrupt=True),
            retcode=0)
  )

  yield (
    api.test('dynamic_local_isolated_script_test_with_passed_json_results') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                    },
                ],
            },
        })
    ) + api.override_step_data('telemetry_gpu_unittests',
            api.test_utils.canned_isolated_script_output(
                passing=True, is_win=False, swarming=False,
                isolated_script_passing=True,
                use_json_test_format=True),
            retcode=0)
  )

  yield (
    api.test('dynamic_local_isolated_script_test_with_custom_results_handler') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'results_handler': 'fake',
                    },
                ],
            },
        })
    ) + api.override_step_data('telemetry_gpu_unittests',
            api.test_utils.canned_isolated_script_output(
                passing=False, is_win=False, swarming=False,
                isolated_script_passing=False,
                use_json_test_format=True),
            retcode=0)
  )

  yield (
    api.test('dynamic_isolated_script_test_harness_failure_zero_retcode') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                    },
                ],
            },
        })
    ) +
    api.override_step_data('telemetry_gpu_unittests',
        api.test_utils.canned_isolated_script_output(
            passing=False, is_win=False, swarming=False,
            isolated_script_passing=False, valid=False),
        retcode=0)
  )

  yield (
    api.test('dynamic_isolated_script_test_harness_failure_no_json') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                    },
                ],
            },
        })
    ) +
    api.override_step_data('telemetry_gpu_unittests',
                           api.json.output(None),
                           retcode=-11)
  )

  yield (
    api.test('build_dynamic_isolated_script_test_compile_target_overriden') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'override_compile_targets': [
                            'abc',
                            'telemetry_gpu_unittests_run'
                        ],
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('build_dynamic_swarmed_isolated_script_test') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test(
        'build_dynamic_swarmed_isolated_script_test_compile_target_overidden') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {'can_use_on_swarming_builders': True},
                        'override_compile_targets': [
                            'telemetry_gpu_unittests_run',
                            'a'
                        ],
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_swarmed_passed_isolated_script_test') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_swarmed_sharded_passed_isolated_script_test') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder',
                           got_revision_cp='refs/heads/master@{#291141}',
                           buildnumber='1234',
                           version='v23523',
                           git_revision='asdfawe2342') +

    api.properties(
      swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
      }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'telemetry_gpu_unittests',
        api.swarming.canned_summary_output(2)
        + api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True,
            shards=2, isolated_script_passing=True,
            use_json_test_format=True, output_chartjson=True),
        retcode=0)
  )

  yield (
    api.test(
        'dynamic_swarmed_sharded_passed_isolated_script_perf_test_histograms') +
    api.properties.generic(mastername='chromium.perf',
                           buildername='Win 10 Perf',
                           parent_buildername='Win Builder',
                           got_revision_cp='refs/heads/master@{#291141}',
                           buildnumber='1234',
                           version='v23523',
                           git_revision='asdfawe2342') +

    api.properties(
      swarm_hashes={
      'telemetry_perf_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
      },**{
         'perf-id': 'testid',
         'results-url': 'https://test-results-url',
         'perf_dashboard_machine_group': 'ChromiumPerf'}) +
    api.platform('win', 64) +
    api.override_step_data(
        'read test spec (chromium.perf.json)',
        api.json.output({
            'Win 10 Perf': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_perf_tests',
                        'name': 'benchmark',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                            'dimension_sets': [
                                {
                                    'gpu': '8086:22b1',
                                    'id': "build187-b4",
                                    'os': "Windows-10-10586",
                                    'pool': "Chrome-perf",
                                },
                            ],
                          'io_timeout': 900,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'benchmark on Intel GPU on Windows on Windows-10-10586',
        api.swarming.canned_summary_output(2)
        + api.test_utils.canned_isolated_script_output(
            passing=True, is_win=True, swarming=True,
            shards=2, isolated_script_passing=True, output_chartjson=True,
            use_json_test_format=True, output_histograms=True),
        retcode=0) +
    api.runtime(is_luci=True, is_experimental=False) +
    # TODO(nednguyen): also assert the content of the benchmark dashboard upload
    # once post_process allows to do so.
    api.post_process(post_process.MustRun, 'benchmark Dashboard Upload') +
    api.post_process(post_process.StatusCodeIn, 0)
  )

  yield (
    api.test('dynamic_swarmed_sharded_passed_isolated_script_perf_test_failed_upload') +
    api.properties.generic(mastername='chromium.perf',
                           buildername='Win 10 Perf',
                           parent_buildername='Win Builder',
                           got_revision_cp='refs/heads/master@{#291141}',
                           buildnumber='1234',
                           version='v23523',
                           git_revision='asdfawe2342') +

    api.properties(
      swarm_hashes={
      'telemetry_perf_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
      }, **{'perf-id': 'testid', 'results-url': 'https://test-results-url'}) +
    api.platform('win', 64) +
    api.override_step_data(
        'read test spec (chromium.perf.json)',
        api.json.output({
            'Win 10 Perf': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_perf_tests',
                        'name': 'benchmark',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                            'dimension_sets': [
                                {
                                    'gpu': '8086:22b1',
                                    'id': "build187-b4",
                                    'os': "Windows-10-10586",
                                    'pool': "Chrome-perf",
                                },
                            ],
                          'io_timeout': 900,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'benchmark on Intel GPU on Windows on Windows-10-10586',
        api.swarming.canned_summary_output(2)
        + api.test_utils.canned_isolated_script_output(
            passing=True, is_win=True, swarming=True,
            shards=2, isolated_script_passing=True,
            output_chartjson=True, use_json_test_format=True),
        retcode=0) +
    api.runtime(is_luci=True, is_experimental=False) +
    # Status code is 1 because this builder is missing
    # perf_dashboard_machine_group property.
    api.post_process(post_process.StatusCodeIn, 1)
  )

  yield (
    api.test('dynamic_swarmed_isolated_script_perf_test_ignore_task_failure') +
    api.properties.generic(mastername='chromium.perf',
                           buildername='Win 10 Perf',
                           parent_buildername='Win Builder',
                           got_revision_cp='refs/heads/master@{#291141}',
                           buildnumber='1234',
                           version='v23523',
                           git_revision='asdfawe2342') +

    api.properties(
      swarm_hashes={
      'telemetry_perf_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
      }, **{'perf-id': 'testid', 'results-url': 'https://test-results-url'}) +
    api.platform('win', 64) +
    api.override_step_data(
        'read test spec (chromium.perf.json)',
        api.json.output({
            'Win 10 Perf': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_perf_tests',
                        'name': 'benchmark',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                            'ignore_task_failure': True,
                            'dimension_sets': [
                                {
                                    'gpu': '8086:22b1',
                                    'id': "build187-b4",
                                    'os': "Windows-10-10586",
                                    'pool': "Chrome-perf",
                                },
                            ],
                          'io_timeout': 900,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'benchmark on Intel GPU on Windows on Windows-10-10586',
        api.swarming.canned_summary_output(2)
        + api.test_utils.canned_isolated_script_output(
            passing=False, is_win=True, swarming=True,
            shards=2, isolated_script_passing=False,
            use_json_test_format=True, output_chartjson=True),
        retcode=1))

  yield (
    api.test('dynamic_swarmed_sharded_passed_isolated_script_perf_test_no_chartjson') +
    api.properties.generic(mastername='chromium.perf',
                           buildername='Win 10 Perf',
                           parent_buildername='Win Builder',
                           got_revision_cp='refs/heads/master@{#291141}',
                           buildnumber='1234',
                           version='v23523',
                           git_revision='asdfawe2342') +

    api.properties(
      swarm_hashes={
      'telemetry_perf_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
      }, **{'perf-id': 'testid', 'results-url': 'http://test-results-url'}) +
    api.platform('win', 64) +
    api.override_step_data(
        'read test spec (chromium.perf.json)',
        api.json.output({
            'Win 10 Perf': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_perf_tests',
                        'name': 'benchmark',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                            'dimension_sets': [
                                {
                                    'gpu': '8086:22b1',
                                    'id': "build187-b4",
                                    'os': "Windows-10-10586",
                                    'pool': "Chrome-perf",
                                },
                            ],
                          'io_timeout': 900,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'benchmark on Intel GPU on Windows on Windows-10-10586',
        api.swarming.canned_summary_output(2)
        + api.test_utils.canned_isolated_script_output(
            passing=True, is_win=True, swarming=True,
            shards=2, isolated_script_passing=True,
            output_chartjson=False, use_json_test_format=True),
        retcode=0)
  )

  yield (
    api.test(
        'dynamic_swarmed_sharded_passed_isolated_script_perf_test_disabled') +
    api.properties.generic(mastername='chromium.perf',
                           buildername='Win 10 Perf',
                           parent_buildername='Win Builder',
                           got_revision_cp='refs/heads/master@{#291141}',
                           buildnumber='1234',
                           version='v23523',
                           git_revision='asdfawe2342') +

    api.properties(
      swarm_hashes={
      'telemetry_perf_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
      }, **{'perf-id': 'testid', 'results-url': 'https://test-results-url'}) +
    api.platform('win', 64) +
    api.override_step_data(
        'read test spec (chromium.perf.json)',
        api.json.output({
            'Win 10 Perf': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_perf_tests',
                        'name': 'benchmark',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                            'dimension_sets': [
                                {
                                    'gpu': '8086:22b1',
                                    'id': "build187-b4",
                                    'os': "Windows-10-10586",
                                    'pool': "Chrome-perf",
                                },
                            ],
                          'io_timeout': 900,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'benchmark on Intel GPU on Windows on Windows-10-10586',
        api.swarming.canned_summary_output(2)
        + api.test_utils.canned_isolated_script_output(
            passing=True, is_win=True, swarming=True,
            shards=2, isolated_script_passing=True,
            output_chartjson=True, benchmark_enabled=False,
            use_json_test_format=True),
        retcode=0) +
    api.post_process(post_process.Filter(
        'benchmark on Intel GPU on Windows on Windows-10-10586'))
  )

  yield (
    api.test(
        'dynamic_swarmed_sharded_passed_isolated_script_perf_test_empty') +
    api.properties.generic(mastername='chromium.perf',
                           buildername='Win 10 Perf',
                           parent_buildername='Win Builder',
                           got_revision_cp='refs/heads/master@{#291141}',
                           buildnumber='1234',
                           version='v23523',
                           git_revision='asdfawe2342') +

    api.properties(
      swarm_hashes={
      'telemetry_perf_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
      }, **{'perf-id': 'testid', 'results-url': 'https://test-results-url'}) +
    api.platform('win', 64) +
    api.override_step_data(
        'read test spec (chromium.perf.json)',
        api.json.output({
            'Win 10 Perf': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_perf_tests',
                        'name': 'benchmark',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                            'dimension_sets': [
                                {
                                    'gpu': '8086:22b1',
                                    'id': "build187-b4",
                                    'os': "Windows-10-10586",
                                    'pool': "Chrome-perf",
                                },
                            ],
                          'io_timeout': 900,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'benchmark on Intel GPU on Windows on Windows-10-10586',
        api.swarming.canned_summary_output(2)
        + api.test_utils.canned_isolated_script_output(
            passing=True, is_win=True, swarming=True,
            shards=1, isolated_script_passing=True,
            output_chartjson=True, benchmark_enabled=False, empty_shards=[1],
            use_json_test_format=True),
        retcode=0)
  )

  yield (
    api.test('dynamic_swarmed_sharded_corrupt_json_isolated_script_test') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 3,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'telemetry_gpu_unittests',
        api.swarming.canned_summary_output(3)
        + api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True,
            shards=3, isolated_script_passing=True, corrupt=True,
            use_json_test_format=True, output_chartjson=True),
        retcode=0)
  )

  yield (
    api.test('dynamic_swarmed_sharded_invalid_json_isolated_script_test') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 3,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data('telemetry_gpu_unittests',
        api.json.output({'version': 2}),
        retcode=0)
  )

  yield (
    api.test('dynamic_swarmed_sharded_failed_isolated_script_test') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'telemetry_gpu_unittests',
        api.swarming.canned_summary_output(2)
        + api.test_utils.canned_isolated_script_output(
            passing=False, is_win=False, swarming=True,
            shards=2, isolated_script_passing=False,
            use_json_test_format=True), retcode=1)
  )

  yield (
    api.test('dynamic_swarmed_sharded_isolated_script_test_missing_shard') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
      'telemetry_gpu_unittests',
      api.swarming.canned_summary_output(2)
      + api.test_utils.canned_isolated_script_output(
        passing=True, is_win=False, swarming=True,
        shards=2, isolated_script_passing=True, valid=True,
        missing_shards=[1]),
      retcode=1)
  )

  yield (
    api.test('dynamic_swarmed_sharded_isolated_script_test_harness_failure') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
      'telemetry_gpu_unittests',
      api.swarming.canned_summary_output(2)
      + api.test_utils.canned_isolated_script_output(
        passing=True, is_win=False, swarming=True,
        shards=2, isolated_script_passing=True, valid=True,
        empty_shards=[1]),
      retcode=1)
  )

  yield (
    api.test(
      'dynamic_swarmed_sharded_isolated_chartjson_test_harness_failure') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
      'telemetry_gpu_unittests',
      api.swarming.canned_summary_output(2)
      + api.test_utils.canned_isolated_script_output(
        passing=True, is_win=False, swarming=True,
        shards=4, isolated_script_passing=True,
        empty_shards=[1], output_chartjson=True,
        use_json_test_format=True),
      retcode=1)
  )

  yield (
    api.test('dynamic_swarmed_sharded_isolated_chartjson_test_disabled') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder',
                           got_revision_cp='refs/heads/master@{#291141}') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'telemetry_gpu_unittests',
        api.swarming.canned_summary_output(2)
        + api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True,
            shards=2, isolated_script_passing=True,
            output_chartjson=True, benchmark_enabled=False,
            use_json_test_format=True),
        retcode=0)
  )

  yield (
    api.test(
        'dynamic_swarmed_sharded_isolated_chartjson_test_missing_all_shards') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder',
                           got_revision_cp='refs/heads/master@{#291141}'
                           ) +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
      'telemetry_gpu_unittests',
      api.swarming.canned_summary_output(2)
      + api.test_utils.canned_isolated_script_output(
        passing=True, is_win=False, swarming=True,
        shards=2, isolated_script_passing=True,
        missing_shards=[1], output_chartjson=True, use_json_test_format=True),
      retcode=1) +
    api.post_process(
        post_process.DoesNotRun, 'telemetry_gpu_unittests Dashboard Upload') +
    api.post_process(
        post_process.Filter('telemetry_gpu_unittests'))
  )

  yield (
    api.test('dynamic_swarmed_sharded_isolated_chartjson_test_missing_shard') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder',
                           got_revision_cp='refs/heads/master@{#291141}'
                           ) +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'shards': 2,
                        },
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
      'telemetry_gpu_unittests',
      api.swarming.canned_summary_output(2)
      + api.test_utils.canned_isolated_script_output(
        passing=True, is_win=False, swarming=True,
        shards=2, isolated_script_passing=True,
        missing_shards=[1], output_chartjson=True, use_json_test_format=True),
      retcode=1)
  )

  yield (
    api.test('dynamic_swarmed_isolated_script_test_linux_gpu') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'dimension_sets': [
                                {
                                    'gpu': '10de:104a',  # NVIDIA GeForce GT 610
                                    'os': 'Linux',
                                },
                            ],
                        },
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_swarmed_isolated_script_test_mac_gpu') +
    api.properties.generic(mastername='chromium.mac',
                           buildername='Mac10.13 Tests',
                           parent_buildername='Mac Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('mac', 64) +
    api.override_step_data(
        'read test spec (chromium.mac.json)',
        api.json.output({
            'Mac10.13 Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'dimension_sets': [
                                {
                                    'gpu': '8086:0a2e',  # Intel Iris
                                    'hidpi': '0',
                                    'os': 'Mac-10.10',
                                }, {
                                    'gpu': '10de:0fe9',  # NVIDIA GeForce GT750M
                                    'hidpi': '1',
                                    'os': 'Mac-10.13',
                                },
                            ],
                        },
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_swarmed_isolated_script_test_win_gpu') +
    api.properties.generic(mastername='chromium.win',
                           buildername='Win7 Tests (1)',
                           parent_buildername='Win Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('win', 64) +
    api.override_step_data(
        'read test spec (chromium.win.json)',
        api.json.output({
            'Win7 Tests (1)': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'dimension_sets': [
                                {
                                    # NVIDIA GeForce GT 610
                                    'gpu': '10de:104a',
                                    'os': 'Windows',
                                }, {
                                    # AMD Radeon HD 6450
                                    'gpu': '1002:6779',
                                    'os': 'Windows',
                                }, {
                                    # VMWare SVGA II Adapter
                                    'gpu': '15ad:0405',
                                    'os': 'Windows',
                                },
                            ],
                        },
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_swarmed_isolated_script_test_win_non_gpu') +
    api.properties.generic(mastername='chromium.win',
                           buildername='Win7 Tests (1)',
                           parent_buildername='Win Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('win', 64) +
    api.override_step_data(
        'read test spec (chromium.win.json)',
        api.json.output({
            'Win7 Tests (1)': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'dimension_sets': [
                                {
                                  'os': 'Windows',
                                },
                            ],
                        },
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_swarmed_failed_isolated_script_test') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'telemetry_gpu_unittests',
        api.swarming.canned_summary_output()
        + api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True,
            isolated_script_passing=False, valid=True),
        retcode=255)
  )

  yield (
    api.test('dynamic_swarmed_passed_with_bad_retcode_isolated_script_test') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_gpu_unittests',
                        'name': 'telemetry_gpu_unittests',
                        'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'telemetry_gpu_unittests',
        api.swarming.canned_summary_output()
        + api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True,
            isolated_script_passing=True, valid=True),
        retcode=255)
  )

  yield (
    api.test(
        'dynamic_swarmed_passed_isolated_script_test_with_swarming_failure') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'telemetry_gpu_unittests',
        api.swarming.canned_summary_output(internal_failure=True)
        + api.test_utils.canned_isolated_script_output(
            passing=False, is_win=False, swarming=True,
            swarming_internal_failure=True, isolated_script_passing=True,
            valid=True),
        retcode=255)
  )

  yield (
    api.test(
        'dynamic_swarmed_isolated_script_test_failure_no_result_json') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.properties(swarm_hashes={
      'telemetry_gpu_unittests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
    ) +
    api.override_step_data(
        'telemetry_gpu_unittests',
        api.swarming.canned_summary_output(failure=True)
        + api.json.output({}),
        retcode=1)
  )

  yield (
    api.test('dynamic_instrumentation_test') +
    api.properties.generic(mastername='chromium.android',
                           buildername='KitKat Phone Tester (rel)') +
    api.override_step_data(
        'read test spec (chromium.android.json)',
        api.json.output({
            'KitKat Phone Tester (rel)': {
                'instrumentation_tests': [
                    {
                        'test': 'ChromePublicTest',
                        'test_apk': 'one_apk',
                        'apk_under_test': 'second_apk',
                        'additional_apks': [
                            'another_apk',
                            'omg_so_many_apks',
                        ],
                    }
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_instrumentation_test_custom_name') +
    api.properties.generic(mastername='chromium.android',
                           buildername='KitKat Phone Tester (rel)') +
    api.override_step_data(
        'read test spec (chromium.android.json)',
        api.json.output({
            'KitKat Phone Tester (rel)': {
                'instrumentation_tests': [
                    {
                        'name': 'custom_test_name',
                        'test': 'default_test_name',
                        'test_apk': 'one_apk',
                        'apk_under_test': 'second_apk',
                        'additional_apks': [
                            'another_apk',
                            'omg_so_many_apks',
                        ],
                    }
                ],
            },
        })
    ) +
    api.post_process(post_process.MustRun, 'custom_test_name') +
    api.post_process(post_process.DoesNotRun, 'default_test_name')
  )

  yield (
    api.test('dynamic_instrumentation_nodefault_build') +
    api.properties.generic(mastername='chromium.android',
                           buildername='KitKat Phone Tester (rel)') +
    api.override_step_data(
        'read test spec (chromium.android.json)',
        api.json.output({
            'KitKat Phone Tester (rel)': {
                'instrumentation_tests': [
                    {
                        'test': 'chrome_public_test_apk',
                    }
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_instrumentation_nodefault_test') +
    api.properties.generic(mastername='chromium.android',
                           buildername='KitKat Phone Tester (rel)') +
    api.override_step_data(
        'read test spec (chromium.android.json)',
        api.json.output({
            'KitKat Phone Tester (rel)': {
                'instrumentation_tests': [
                    {
                        'test': 'chrome_public_test_apk',
                    }
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_swarmed_gn_instrumentation_test') +
    api.properties.generic(mastername='chromium.android',
                           buildername='KitKat Phone Tester (rel)') +
    api.override_step_data(
        'read test spec (chromium.android.json)',
        api.json.output({
            'KitKat Phone Tester (rel)': {
                'gtest_tests': [
                    {
                        'test': 'chrome_public_test_apk',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                            'dimension_sets': [
                                {
                                    'build.id': 'KTU84P',
                                    'product.board': 'hammerhead',
                                },
                            ],
                            'cipd_packages': [
                                {
                                    'location': '{$HOME}/logdog',
                                    'cipd_package': 'infra/logdog/linux-386',
                                    'revision': 'git_revision:deadbeef',
                                },
                            ],
                        },
                        'override_compile_targets': [
                            'chrome_public_test_apk'
                         ],
                        'override_isolate_target': 'chrome_public_test_apk',
                    }
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_instrumentation_test_with_timeout_scale') +
    api.properties.generic(mastername='chromium.android.fyi',
                           buildername='Lollipop Low-end Tester',
                           parent_mastername='chromium.android',
                           parent_buildername='Android arm Builder (dbg)') +
    api.override_step_data(
        'read test spec (chromium.android.fyi.json)',
        api.json.output({
            'Lollipop Low-end Tester': {
                'instrumentation_tests': [
                    {
                      'test': 'ChromePublicTest',
                      'timeout_scale': 2,
                    }
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_junit_test') +
    api.properties.generic(mastername='chromium.android',
                           buildername='KitKat Phone Tester (rel)') +
    api.override_step_data(
        'read test spec (chromium.android.json)',
        api.json.output({
            'KitKat Phone Tester (rel)': {
                'junit_tests': [
                    {
                        'test': 'base_junit_tests',
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_gtest_on_builder') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
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
        })
    )
  )

  yield (
    api.test('dynamic_gtest_win') +
    api.properties.generic(mastername='chromium.win',
                           buildername='Win7 Tests (1)',
                           parent_buildername='Win Builder') +
    api.platform('win', 64) +
    api.override_step_data(
        'read test spec (chromium.win.json)',
        api.json.output({
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
        })
    )
  )

  yield (
    api.test('dynamic_gtest_android') +
    api.properties.generic(mastername='chromium.android',
                           buildername='Lollipop Phone Tester',
                           parent_buildername='Android arm Builder (dbg)') +
    api.override_step_data(
        'read test spec (chromium.android.json)',
        api.json.output({
            'Lollipop Phone Tester': {
                'gtest_tests': [
                    {
                      'test': 'base_unittests',
                    }
                ],
            },
        }))
  )

  yield (
    api.test('dynamic_gtest_fuchsia') +
    api.properties.generic(mastername='chromium.fyi',
                           buildername='Fuchsia') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.fyi.json)',
        api.json.output({
            'Fuchsia': {
                'gtest_tests': [
                    {
                      'test': 'base_unittests',
                    }
                ],
            },
        }))
  )

  # Tests switching on asan and swiching off lsan for sandbox tester.
  yield (
    api.test('dynamic_gtest_memory_asan_no_lsan') +
    api.properties.generic(mastername='chromium.memory',
                           buildername='Linux ASan Tests (sandboxed)',
                           parent_buildername='Linux ASan LSan Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.memory.json)',
        api.json.output({
            'Linux ASan Tests (sandboxed)': {
                'gtest_tests': [
                    'browser_tests',
                ],
            },
        })
    )
  )

  # Tests that the memory builder is using the correct compile targets.
  yield (
    api.test('dynamic_gtest_memory_builder') +
    api.properties.generic(mastername='chromium.memory',
                           buildername='Linux ASan LSan Builder',
                           revision='123456') +
    api.platform('linux', 64) +
    # The builder should build 'browser_tests', because there exists a child
    # tester that uses that test.
    api.override_step_data(
        'read test spec (chromium.memory.json)',
        api.json.output({
            'Linux ASan Tests (sandboxed)': {
                'gtest_tests': [
                    'browser_tests',
                ],
            },
        })
    )
  )

  # Tests that the memory mac tester is using the correct test flags.
  yield (
    api.test('dynamic_gtest_memory_mac64') +
    api.properties.generic(
        mastername='chromium.memory',
        buildername='Mac ASan 64 Tests (1)',
        parent_buildername='Mac ASan 64 Builder') +
    api.platform('mac', 64) +
    api.override_step_data(
        'read test spec (chromium.memory.json)',
        api.json.output({
            'Mac ASan 64 Tests (1)': {
                'gtest_tests': [
                    'browser_tests',
                ],
            },
        })
    )
  )

  yield (
    api.test('tsan') +
    api.properties.generic(mastername='chromium.memory',
                           buildername='Linux TSan Tests',
                           parent_buildername='Linux TSan Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.memory.json)',
        api.json.output({
            'Linux TSan Tests': {
                'compile_targets': ['base_unittests'],
                'gtest_tests': ['base_unittests'],
            },
        })
    )
  )

  yield (
    api.test('msan') +
    api.properties.generic(mastername='chromium.memory',
                           buildername='Linux MSan Tests',
                           parent_buildername='Linux MSan Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.memory.json)',
        api.json.output({
            'Linux MSan Tests': {
                'compile_targets': ['base_unittests'],
                'gtest_tests': ['base_unittests'],
            },
        })
    )
  )

  yield (
    api.test('buildnumber_zero') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder',
                           buildnumber=0) +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
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
        })
    )
  )

  yield (
    api.test('one_failure_keeps_going_dynamic_tests') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
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
        })
    ) +
    api.override_step_data('base_unittests', retcode=1)
  )

  yield (
    api.test('dynamic_script_test_with_args') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'scripts': [
                    {
                        'name': 'media_perftests',
                        'script': 'gtest_perf_test.py',
                        'args': ['media_perftests', '--single-process-tests']
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('dynamic_script_test_failure') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'scripts': [
                    {
                      'name': 'test_script_with_broken_tests',
                      'script': 'test_script_with_broken_tests.py'
                    }
                ]
            }
        })
    ) +
    api.override_step_data('test_script_with_broken_tests',
                           api.json.output({
      'valid': True,
      'failures': ['FailSuite.Test1', 'FlakySuite.TestA']
    }))
  )

  yield (
    api.test('chromium_webkit_revision_webkit') +
    api.properties.generic(mastername='chromium.webkit',
                           buildername='WebKit Linux Trusty',
                           project='webkit',
                           revision='191187') +
    api.platform('linux', 64)
  )

  yield (
    api.test('chromium_webkit_revision_chromium') +
    api.properties.generic(
        mastername='chromium.webkit',
        buildername='WebKit Linux Trusty',
        project='chromium',
        revision='3edb4989f8f69c968c0df14cb1c26d21dd19bf1f') +
    api.platform('linux', 64)
  )

  yield (
    api.test('chromium_webkit_parent_revision_webkit') +
    api.properties.generic(
        mastername='chromium.webkit',
        buildername='WebKit Win7',
        project='webkit',
        parent_buildername='WebKit Win Builder',
        parent_got_revision='7496f63cbefd34b2d791022fbad64a82838a3f3f',
        parent_got_webkit_revision='191275',
        revision='191275') +
    api.platform('win', 32)
  )

  yield (
    api.test('chromium_webkit_parent_revision_chromium') +
    api.properties.generic(
        mastername='chromium.webkit',
        buildername='WebKit Win7',
        project='chromium',
        parent_buildername='WebKit Win Builder',
        parent_got_revision='1e74b372f951d4491f305ec64f6decfcda739e73',
        parent_got_webkit_revision='191269',
        revision='1e74b372f951d4491f305ec64f6decfcda739e73') +
    api.platform('win', 32)
  )

  yield (
    api.test('kitchen_path_config') +
    api.properties(
        mastername='chromium.fyi',
        buildername='Linux remote_run Builder',
        bot_id='build1-a1',
        buildnumber='77457',
        path_config='kitchen')
  )

  yield (
    api.test('generic_path_config') +
    api.properties(
        mastername='chromium.fyi',
        buildername='Linux remote_run Builder',
        bot_id='build1-a1',
        buildnumber='77457',
        path_config='generic')
  )

  yield (
    api.test('ensure_goma_fail') +
    api.properties(
        mastername='chromium.fyi',
        buildername='Linux remote_run Builder',
        bot_id='build1-a1',
        buildnumber='77457',
        path_config='kitchen') +
    api.override_step_data('ensure_goma.ensure_installed', retcode=1)
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

  yield (
    api.test('gtest_custom_merge_script') +
    api.properties.generic(mastername='chromium.linux',
                           parent_buildername='Linux Builder',
                           buildername='Linux Tests') +
    api.platform('linux', 64) +
    api.properties(swarm_hashes={
      'browser_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'gtest_tests': [
                    {
                        'test': 'browser_tests',
                        'swarming': {'can_use_on_swarming_builders': True},
                        'merge': {
                            'script': '//fake_merge_script.py',
                        },
                    },
                ],
            },
        })
    ) +
    api.post_process(post_process.Filter('browser_tests'))
  )

  yield (
    api.test('gtest_bad_custom_merge_script') +
    api.properties.generic(mastername='chromium.linux',
                           parent_buildername='Linux Builder',
                           buildername='Linux Tests') +
    api.platform('linux', 64) +
    api.properties(swarm_hashes={
      'browser_tests': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'gtest_tests': [
                    {
                        'test': 'browser_tests',
                        'swarming': {'can_use_on_swarming_builders': True},
                        'merge': {
                            'script': 'fake_merge_script.py',
                        },
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('isolated_script_test_custom_merge_script') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.properties(swarm_hashes={
      'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.step_data('fake_test', api.json.output(json_results)) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'fake_test',
                      'name': 'fake_test',
                      'merge': {
                        'script': '//fake_merge_script.py',
                      },
                      'swarming': {
                        'can_use_on_swarming_builders': True,
                      },
                    },
                ],
            },
        })
    ) +
    api.post_process(post_process.Filter('fake_test'))
  )

  yield (
    api.test('isolated_script_test_bad_custom_merge_script') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.properties(swarm_hashes={
      'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'fake_test',
                      'name': 'fake_test',
                      'merge': {
                        'script': 'bad_fake_merge_script.py',
                      },
                      'swarming': {
                        'can_use_on_swarming_builders': True,
                      },
                    },
                ],
            },
        })
    )
  )

  yield (
    api.test('isolated_script_test_custom_merge_script_with_args') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.properties(swarm_hashes={
      'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.step_data('fake_test', api.json.output(json_results)) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'fake_test',
                      'name': 'fake_test',
                      'merge': {
                        'script': '//fake_merge_script.py',
                        'args': [
                          '--foo', 'foo_value',
                        ],
                      },
                      'swarming': {
                        'can_use_on_swarming_builders': True,
                      },
                    },
                ],
            },
        })
    ) +
    api.post_process(post_process.Filter('fake_test'))
  )

  yield (
    api.test('isolated_script_test_custom_results_handler') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.properties(swarm_hashes={
      'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.step_data('fake_test', api.json.output(json_results)) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'fake_test',
                      'name': 'fake_test',
                      'results_handler': 'fake',
                      'swarming': {
                        'can_use_on_swarming_builders': True,
                      },
                    },
                ],
            },
        })
    ) +
    api.post_process(post_process.Filter('fake_test'))
  )

  yield (
    api.test('isolated_script_test_invalid_results_handler') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.properties(swarm_hashes={
      'fake_test': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    }) +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'fake_test',
                      'name': 'fake_test',
                      'results_handler': 'unknown',
                    },
                ],
            },
        })
    )
  )

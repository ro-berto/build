# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import json

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from PB.recipe_engine import result as result_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'code_coverage',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'test_utils',
]

PROPERTIES = {'fail_compile': Property(default=False, kind=bool)}


def _builder_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-example-archive', **kwargs)


CUSTOM_BUILDERS = bot_db.BotDatabase.create({
    'chromium.example': {
        'Isolated Transfer Builder':
            _builder_spec(
                bot_type='builder',
                chromium_apply_config=['mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                gclient_config='chromium',
                testing={
                    'platform': 'linux',
                },
            ),
        'Isolated Transfer Tester':
            _builder_spec(
                bot_type='tester',
                chromium_apply_config=['mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                gclient_config='chromium',
                parent_buildername='Isolated Transfer Builder',
                testing={
                    'platform': 'linux',
                },
            ),
        'Isolated Transfer: mixed builder, isolated tester (builder)':
            _builder_spec(
                bot_type='builder',
                chromium_apply_config=['mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                gclient_config='chromium',
                testing={
                    'platform': 'linux',
                },
            ),
        'Isolated Transfer: mixed builder, isolated tester (tester)':
            _builder_spec(
                bot_type='tester',
                chromium_apply_config=['mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                gclient_config='chromium',
                parent_buildername=('Isolated Transfer: '
                                    'mixed builder, isolated tester (builder)'),
                testing={
                    'platform': 'linux',
                },
            ),
        'Isolated Transfer: mixed BT, isolated tester (BT)':
            _builder_spec(
                android_config='main_builder_mb',
                bot_type='builder_tester',
                chromium_config='android',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                },
                gclient_config='chromium',
                testing={
                    'platform': 'linux',
                },
            ),
        'Isolated Transfer: mixed BT, isolated tester (tester)':
            _builder_spec(
                android_config='main_builder_mb',
                bot_type='tester',
                chromium_config='android',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_PLATFORM': 'android',
                },
                gclient_config='chromium',
                parent_buildername=
                'Isolated Transfer: mixed BT, isolated tester (BT)',
                testing={
                    'platform': 'linux',
                },
            ),
        'Packaged Transfer Builder':
            _builder_spec(
                bot_type='builder',
                chromium_apply_config=['mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                gclient_config='chromium',
                testing={
                    'platform': 'linux',
                },
            ),
        'Packaged Transfer Enabled Builder':
            _builder_spec(
                bot_type='builder',
                enable_package_transfer=True,
                chromium_apply_config=['mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                gclient_config='chromium',
                testing={
                    'platform': 'linux',
                },
            ),
        'Packaged Transfer Tester':
            _builder_spec(
                bot_type='tester',
                chromium_apply_config=['mb'],
                chromium_config='chromium',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                gclient_config='chromium',
                parent_buildername='Packaged Transfer Builder',
                testing={
                    'platform': 'linux',
                },
            ),
        'Multiple Triggers: Builder':
            _builder_spec(
                android_config='main_builder',
                bot_type='builder',
                chromium_apply_config=['mb'],
                chromium_config='android',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                    'TARGET_PLATFORM': 'android',
                },
                gclient_apply_config=['android'],
                gclient_config='chromium',
                testing={
                    'platform': 'linux',
                },
            ),
        'Multiple Triggers: Mixed':
            _builder_spec(
                android_config='main_builder',
                bot_type='tester',
                chromium_apply_config=['mb'],
                chromium_config='android',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                    'TARGET_PLATFORM': 'android',
                },
                gclient_apply_config=['android'],
                gclient_config='chromium',
                parent_buildername='Multiple Triggers: Builder',
                testing={
                    'platform': 'linux',
                },
            ),
        'Multiple Triggers: Isolated':
            _builder_spec(
                android_config='main_builder',
                bot_type='tester',
                chromium_apply_config=['mb'],
                chromium_config='android',
                chromium_config_kwargs={
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                    'TARGET_PLATFORM': 'android',
                },
                gclient_apply_config=['android'],
                gclient_config='chromium',
                parent_buildername='Multiple Triggers: Builder',
                testing={
                    'platform': 'linux',
                },
            ),
    },
})


def NotIdempotent(check, step_odict, step):
  check('Idempotent flag unexpected',
        '--idempotent' not in step_odict[step].cmd)


def RunSteps(api, fail_compile):
  api.path.mock_add_paths(
      api.code_coverage.profdata_dir().join('merged.profdata'))

  # override compile_specific_targets to control compile step failure state
  def compile_override(*args, **kwargs):
    return result_pb2.RawResult(
        status=common_pb2.FAILURE, summary_markdown='Compile step failed.')

  if fail_compile:
    api.chromium_tests.compile_specific_targets = compile_override

  return api.chromium_tests.main_waterfall_steps()


def GenTests(api):
  yield api.test(
      'builder',
      api.chromium_tests.platform([{
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder'
      }]),
      api.chromium.ci_build(
          mastername='chromium.linux', builder='Linux Builder'),
      api.runtime(is_luci=True, is_experimental=False),
      api.override_step_data(
          'trigger',
          stdout=api.raw_io.output_text("""
        {
          "builds":[{
           "status": "SCHEDULED",
           "created_ts": "1459200369835900",
           "bucket": "user.username",
           "result_details_json": "null",
           "status_changed_ts": "1459200369835930",
           "created_by": "user:username@example.com",
           "updated_ts": "1459200369835940",
           "utcnow_ts": "1459200369962370",
           "parameters_json": "{\\"This_has_been\\": \\"removed\\"}",
           "id": "9016911228971028736"
          }],
          "kind": "buildbucket#resourcesItem",
          "etag": "\\"8uCIh8TRuYs4vPN3iWmly9SJMqw\\""
        }
      """)),
  )

  yield api.test(
      'tester',
      api.chromium_tests.platform([{
          'mastername': 'chromium.linux',
          'buildername': 'Linux Tests'
      }]),
      api.chromium.ci_build(
          mastername='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
  )

  yield api.test(
      'code_coverage_ci_bots',
      api.chromium.ci_build(
          mastername='chromium.fyi', builder='linux-chromeos-code-coverage'),
      api.properties(
          swarm_hashes={'base_unittests': '[dummy hash for base_unittests]'}),
      api.code_coverage(use_clang_coverage=True),
      api.chromium_tests.read_source_side_spec(
          'chromium.fyi', {
              'linux-chromeos-code-coverage': {
                  'gtest_tests': [{
                      'isolate_coverage_data': True,
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.override_step_data(
          'base_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), internal_failure=True)),
      api.post_process(post_process.MustRun, 'base_unittests (retry shards)'),
      api.post_process(
          post_process.MustRun, 'process clang code coverage data.'
          'generate metadata for 2 tests'),
      api.post_process(
          NotIdempotent,
          'test_pre_run (retry shards).[trigger] base_unittests (retry shards)'
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'java_code_coverage_ci_bots',
      api.chromium.ci_build(
          mastername='chromium.fyi', builder='android-code-coverage'),
      api.properties(swarm_hashes={
          'chrome_public_test_apk': '[dummy hash for chrome_public_test_apk]'
      }),
      api.code_coverage(use_java_coverage=True),
      api.chromium_tests.read_source_side_spec(
          'chromium.fyi', {
              'android-code-coverage': {
                  'gtest_tests': [{
                      'isolate_coverage_data': True,
                      'test': 'chrome_public_test_apk',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.post_process(post_process.MustRun,
                       'chrome_public_test_apk on Android'),
      api.post_process(post_process.MustRun, 'process java coverage'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  def TriggersBuilderWithProperties(check,
                                    step_odict,
                                    builder='',
                                    properties=None):
    trigger_step = step_odict['trigger']
    check(
        '"trigger" step did not run expected command.',
        'scheduler.Scheduler.EmitTriggers' in trigger_step.cmd and
        trigger_step.stdin)
    trigger_json = json.loads(trigger_step.stdin)

    for batch in trigger_json.get('batches', []):
      if any(builder == j.get('job') for j in batch.get('jobs', [])):
        actual_properties = (
            batch.get('trigger', {}).get('buildbucket', {}).get(
                'properties', {}))
        check(all(p in actual_properties for p in properties))
        break
    else:  # pragma: no cover
      check('"%s" not triggered' % builder, False)

  yield api.test(
      'isolate_transfer_builder',
      api.chromium.ci_build(
          mastername='chromium.example',
          builder='Isolated Transfer Builder',
          build_number=123,
          bot_id='isolated_transfer_builder_id'),
      api.chromium_tests.builders(CUSTOM_BUILDERS),
      api.runtime(is_luci=True, is_experimental=False),
      api.chromium_tests.read_source_side_spec(
          'chromium.example', {
              'Isolated Transfer Tester': {
                  'gtest_tests': [{
                      'args': ['--sample-argument'],
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'test': 'base_unittests',
                  },],
              },
          }),
      api.post_process(post_process.DoesNotRun, 'package build'),
      api.post_process(
          TriggersBuilderWithProperties,
          builder='Isolated Transfer Tester',
          properties=['swarm_hashes']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'isolate_transfer_tester',
      api.chromium.ci_build(
          mastername='chromium.example',
          builder='Isolated Transfer Tester',
          parent_buildername='Isolated Transfer Builder',
          build_number=123,
          bot_id='isolated_transfer_tester_id'),
      api.chromium_tests.builders(CUSTOM_BUILDERS),
      api.properties(swarm_hashes={
          'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
      }),
      api.runtime(is_luci=True, is_experimental=False),
      api.chromium_tests.read_source_side_spec(
          'chromium.example', {
              'Isolated Transfer Tester': {
                  'gtest_tests': [{
                      'args': ['--sample-argument'],
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'test': 'base_unittests',
                  },],
              },
          }),
      api.override_step_data('find isolated tests', api.json.output({})),
      api.post_process(post_process.DoesNotRun, 'extract build'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'isolated_transfer__mixed_builder_isolated_tester',
      api.chromium.ci_build(
          mastername='chromium.example',
          builder=(
              'Isolated Transfer: mixed builder, isolated tester (builder)'),
          build_number=123,
          bot_id='isolated_transfer_builder_id'),
      api.chromium_tests.builders(CUSTOM_BUILDERS),
      api.runtime(is_luci=True, is_experimental=False),
      api.chromium_tests.read_source_side_spec(
          'chromium.example', {
              'Isolated Transfer: mixed builder, isolated tester (builder)': {
                  'scripts': [{
                      'name': 'check_network_annotations',
                      'script': 'check_network_annotations.py',
                  },],
              },
              'Isolated Transfer: mixed builder, isolated tester (tester)': {
                  'gtest_tests': [{
                      'args': ['--sample-argument'],
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'test': 'base_unittests',
                  },],
              },
          }),
      api.post_process(post_process.DoesNotRun, 'package build'),
      api.post_process(
          TriggersBuilderWithProperties,
          builder='Isolated Transfer: mixed builder, isolated tester (tester)',
          properties=['swarm_hashes']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'isolated_transfer__mixed_bt_isolated_tester',
      api.chromium.ci_build(
          mastername='chromium.example',
          builder='Isolated Transfer: mixed BT, isolated tester (BT)',
          build_number=123,
          bot_id='isolated_transfer_builder_tester_id'),
      api.chromium_tests.builders(CUSTOM_BUILDERS),
      api.runtime(is_luci=True, is_experimental=False),
      api.override_step_data(
          'read test spec (chromium.example.json)',
          api.json.output({
              'Isolated Transfer: mixed BT, isolated tester (BT)': {
                  'junit_tests': [{
                      'test': 'base_junit_tests',
                  },],
              },
              'Isolated Transfer: mixed BT, isolated tester (tester)': {
                  'gtest_tests': [{
                      'args': ['--sample-argument'],
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'test': 'base_unittests',
                  },],
              },
          })),
      api.post_process(post_process.DoesNotRun, 'package build'),
      api.post_process(
          TriggersBuilderWithProperties,
          builder='Isolated Transfer: mixed BT, isolated tester (tester)',
          properties=['swarm_hashes']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'package_transfer_builder',
      api.chromium.ci_build(
          mastername='chromium.example',
          builder='Packaged Transfer Builder',
          build_number=123,
          bot_id='packaged_transfer_builder_id'),
      api.chromium_tests.builders(CUSTOM_BUILDERS),
      api.chromium_tests.read_source_side_spec(
          'chromium.example', {
              'Packaged Transfer Tester': {
                  'gtest_tests': [{
                      'args': ['--sample-argument'],
                      'swarming': {
                          'can_use_on_swarming_builders': False,
                      },
                      'test': 'base_unittests',
                  },],
              },
          }),
      api.post_process(post_process.MustRun, 'package build'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'package_transfer_enabled_builder',
      api.chromium.ci_build(
          mastername='chromium.example',
          builder='Packaged Transfer Enabled Builder',
          build_number=123,
          bot_id='packaged_transfer_builder_id'),
      api.chromium_tests.builders(CUSTOM_BUILDERS),
      api.chromium_tests.read_source_side_spec(
          'chromium.example', {
              'Packaged Transfer Tester': {
                  'gtest_tests': [{
                      'args': ['--sample-argument'],
                      'swarming': {
                          'can_use_on_swarming_builders': False,
                      },
                      'test': 'base_unittests',
                  },],
              },
          }),
      api.post_process(post_process.MustRun, 'package build'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'package_transfer_tester',
      api.chromium.ci_build(
          mastername='chromium.example',
          builder='Packaged Transfer Tester',
          parent_buildername='Packaged Transfer Builder',
          build_number=123,
          bot_id='packaged_transfer_tester_id'),
      api.chromium_tests.builders(CUSTOM_BUILDERS),
      api.properties(swarm_hashes={
          'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.example', {
              'Packaged Transfer Tester': {
                  'gtest_tests': [{
                      'args': ['--sample-argument'],
                      'swarming': {
                          'can_use_on_swarming_builders': False,
                      },
                      'test': 'base_unittests',
                  },],
              },
          }),
      api.post_process(post_process.MustRun, 'extract build'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'multiple_triggers',
      api.chromium.ci_build(
          mastername='chromium.example',
          builder='Multiple Triggers: Builder',
          build_number=123,
          bot_id='multiple_triggers_builder_id'),
      api.chromium_tests.builders(CUSTOM_BUILDERS),
      api.runtime(is_luci=True, is_experimental=False),
      api.chromium_tests.read_source_side_spec(
          'chromium.example', {
              'Multiple Triggers: Mixed': {
                  'gtest_tests': [{
                      'args': ['--sample-argument'],
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'test': 'base_unittests',
                  },],
                  'junit_tests': [{
                      'test': 'base_junit_tests',
                  },],
              },
              'Multiple Triggers: Isolated': {
                  'gtest_tests': [{
                      'args': ['--sample-argument'],
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'test': 'base_unittests',
                  },],
              },
          }),
      api.post_process(post_process.MustRun, 'package build'),
      api.post_process(
          TriggersBuilderWithProperties,
          builder='Multiple Triggers: Mixed',
          properties=['swarm_hashes']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'compile_failure',
      api.chromium.ci_build(
          mastername='chromium.linux', builder='Linux Builder'),
      api.properties(fail_compile=True),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.ResultReason, 'Compile step failed.'),
      api.post_process(post_process.DropExpectation),
  )

  results_with_failure = {
      'per_iteration_data': [{
          'Suite.Test': [{
              'elapsed_time_ms': 0,
              'output_snippet': '',
              'status': 'FAILURE',
          },],
      }]
  }
  yield api.test(
      'skip_retrying_logic_is_limited_to_try_jobs',
      api.chromium_tests.platform([{
          'mastername': 'chromium.linux',
          'buildername': 'Linux Tests'
      }]),
      api.chromium.ci_build(
          mastername='chromium.linux',
          builder='Linux Tests',
          parent_buildername='Linux Builder'),
      api.properties(**{
          '$build/test_utils': {
              'min_failed_suites_to_skip_retry': 3,
          },
      }),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [
                      'base_unittests', 'target1', 'target2', 'target3'
                  ],
              },
          }),
      api.override_step_data(
          'target1',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=True)),
      api.override_step_data(
          'target2',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=True)),
      api.override_step_data(
          'target3',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results(
                  json.dumps(results_with_failure), retcode=1),
              failure=True)),
      api.post_process(post_process.DoesNotRunRE, 'skip retrying'),
      api.post_process(post_process.DropExpectation),
  )

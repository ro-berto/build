# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" This recipe is to compile and isolate the given isolated targets.

If multiple test targets match the same isolated targets, we default to the
first one after ordering test target names alphabetically.
"""

import json
import re

from recipe_engine import post_process
from recipe_engine.config import List
from recipe_engine.recipe_api import Property

from PB.recipe_engine import result as result_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb


DEPS = [
    'chromium',
    'chromium_android',
    'chromium_checkout',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/git',
    'findit',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/context',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]


PROPERTIES = {
    'target_mastername': Property(
        kind=str, help='The target master to match compile config to.'),
    'target_testername': Property(
        kind=str,
        help='The target tester to match test config to. If the tests are run '
             'on a builder, just treat the builder as a tester.'),
    'revision': Property(
        kind=str, help='The revision to compile at.'),
    'isolated_targets': Property(
        kind=List(str),
        help='The isolated targets to build e.g.: ["browser_tests"]'),
}


def RunSteps(api, target_mastername, target_testername,
             revision, isolated_targets):
  target_buildername, checked_out_revision, cached_revision = (
      api.findit.configure_and_sync(
          api, target_mastername, target_testername, revision,
          builders=api.properties.get('builders')))

  bot_id = api.chromium_tests.create_bot_id(
      target_mastername, target_buildername, target_testername)
  bot_config = api.m.chromium_tests.create_bot_config_object(
      [bot_id], builders=api.properties.get('builders'))
  bot_update_step, bot_db = api.m.chromium_tests.prepare_checkout(
      bot_config, root_solution_revision=revision)

  # Find the matching test targets.
  test_config = api.m.chromium_tests.get_tests(bot_config, bot_db)
  tests = [
      test for test in test_config.all_tests()
      if test.isolate_target in isolated_targets]

  report = {
      'metadata': {},
      'previously_cached_revision': cached_revision,
      'previously_checked_out_revision': checked_out_revision
  }

  raw_result = result_pb2.RawResult(status=common_pb.FAILURE)

  try:
    if tests:
      # Default to first one. For example, the following three test targets
      # match the same underlying isolated target "browser_tests":
      #  * browser_tests
      #  * network_service_browser_tests
      #  * webui_polymer2_browser_tests
      tests.sort(key=lambda t: t.canonical_name)
      compile_targets = tests[0].compile_targets()

      assert compile_targets, 'Test %s has no compile target' % tests[0].name

      raw_result = api.m.chromium_tests.compile_specific_targets(
          bot_config,
          bot_update_step,
          bot_db,
          compile_targets,
          tests_including_triggered=tests[:1],  # Only the first test.
          mb_mastername=target_mastername,
          mb_buildername=target_buildername,
          override_bot_type='builder_tester')
      if raw_result.status != common_pb.SUCCESS:
        return raw_result

      report['isolated_tests'] = api.isolate.isolated_tests
      raw_result.status = common_pb.SUCCESS
  except api.step.InfraFailure:
    report['metadata']['infra_failure'] = True
    raise
  finally:
    report['last_checked_out_revision'] = api.properties.get('got_revision')
    # Give the full report including isolated sha and metadata.
    api.python.succeeding_step(
        'report', [json.dumps(report, indent=2)], as_log='report')

  return raw_result


def GenTests(api):
  def base(isolated_targets, tester_name):
    properties = {
        'path_config': 'kitchen',
        'mastername': 'chromium.findit',
        'bot_id': 'beefy_vm',
        'target_mastername': 'chromium.findit',
        'target_testername': tester_name,
        'revision': 'r0',
        'isolated_targets': isolated_targets,
        'builders': {
            'chromium.findit': {
                'builders': {
                    'findit_builder': {
                        'chromium_config': 'chromium',
                        'chromium_apply_config': [
                          'mb',
                          'goma_high_parallel',
                        ],
                        'gclient_config': 'chromium',
                        'chromium_config_kwargs': {
                          'BUILD_CONFIG': 'Release',
                          'TARGET_BITS': 64,
                        },
                        'bot_type': 'builder',
                        'testing': {
                          'platform': 'linux',
                        },
                        'force_exparchive': 5,
                        'checkout_dir': 'linux',
                    },
                    'findit_tester': {
                        'chromium_config': 'chromium',
                        'chromium_apply_config': ['mb'],
                        'gclient_config': 'chromium',
                        'chromium_config_kwargs': {
                          'BUILD_CONFIG': 'Release',
                          'TARGET_BITS': 64,
                        },
                        'bot_type': 'tester',
                        'parent_buildername': 'findit_builder',
                        'testing': {
                          'platform': 'linux',
                        },
                        'swarming_dimensions': {
                            'os': 'Linux',
                        },
                    },
                    'findit_builder_tester': {
                        'chromium_config': 'chromium',
                        'chromium_apply_config': ['mb'],
                        'gclient_config': 'chromium',
                        'chromium_config_kwargs': {
                          'BUILD_CONFIG': 'Release',
                          'TARGET_BITS': 64,
                        },
                        'bot_type': 'builder_tester',
                        'testing': {
                          'platform': 'linux',
                        },
                        'swarming_dimensions': {
                            'os': 'Linux',
                        },
                    },
                }
            }
        },
    }
    return (
        api.properties(**properties) +
        api.buildbucket.ci_build(
            builder='findit_variable',
            git_repo='https://chromium.googlesource.com/chromium/src',
        ) +
        api.platform.name('linux') +
        api.runtime(True, False)
    )

  def verify_report(check, step_odict, expected_isolated_tests):
    step = step_odict['report']
    report_dict = json.loads(step.logs['report'])

    check(json.dumps(report_dict.get('isolated_tests'), sort_keys=True)
          == json.dumps(expected_isolated_tests, sort_keys=True))
    return step_odict


  yield api.test(
      'no_matching_isolated_target',
      base(['browser_tests'], 'findit_builder_tester'),
      api.chromium_tests.read_source_side_spec(
          'chromium.findit', {
              'findit_tester': {
                  'gtest_tests': [{
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 1
                      },
                  },],
              },
          },
          step_suffix=' (2)'),
      api.post_process(verify_report, None),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'match_exactly_one_test_target',
      base(['browser_tests'], 'findit_tester'),
      api.chromium_tests.read_source_side_spec(
          'chromium.findit', {
              'findit_tester': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 1
                      },
                  },],
              },
          },
          step_suffix=' (2)'),
      api.post_process(verify_report,
                       {'browser_tests': '[dummy hash for browser_tests]'}),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'match_more_than_one_test_target',
      base(['browser_tests'], 'findit_tester'),
      api.chromium_tests.read_source_side_spec(
          'chromium.findit', {
              'findit_tester': {
                  'gtest_tests': [
                      {
                          'test': 'browser_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 1
                          },
                      },
                      {
                          'name': 'network_services_browser_tests',
                          'test': 'browser_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 1
                          },
                      },
                      {
                          'name': 'webui_polymer2_browser_tests',
                          'test': 'browser_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 1
                          },
                      },
                  ],
              },
          },
          step_suffix=' (2)'),
      api.post_process(verify_report,
                       {'browser_tests': '[dummy hash for browser_tests]'}),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'failed_to_compile_goma',
      base(['browser_tests'], 'findit_tester'),
      api.chromium_tests.read_source_side_spec(
          'chromium.findit', {
              'findit_tester': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 1
                      },
                  },],
              },
          },
          step_suffix=' (2)'),
      api.override_step_data('preprocess_for_goma.start_goma', retcode=1),
      api.step_data(
          'preprocess_for_goma.goma_jsonstatus',
          api.json.output(data={
              'notice': [{
                  'infra_status': {
                      'ping_status_code': 408,
                  },
              },],
          })),
      api.post_process(verify_report, None),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'compile_failure',
      base(['browser_tests'], 'findit_tester'),
      api.chromium_tests.read_source_side_spec(
          'chromium.findit', {
              'findit_tester': {
                  'gtest_tests': [{
                      'test': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'shards': 1
                      },
                  },],
              },
          },
          step_suffix=' (2)'),
      api.step_data('compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

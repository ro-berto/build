# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" This recipe is to compile and isolate the given isolated targets.

If multiple test targets match the same isolated targets, we default to the
first one after ordering test target names alphabetically.
"""

import json

from recipe_engine import post_process
from recipe_engine.config import List
from recipe_engine.recipe_api import Property

from PB.recipe_engine import result as result_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'builder_group',
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'findit',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]


PROPERTIES = {
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


def RunSteps(api, target_testername, revision, isolated_targets):
  target_builder_group = api.builder_group.for_target
  target_tester_id = chromium.BuilderId.create_for_group(
      target_builder_group, target_testername)
  bot_mirror, checked_out_revision, cached_revision = (
      api.findit.configure_and_sync(target_tester_id, revision))

  builder_config = api.findit.get_builder_config_for_mirror(bot_mirror)
  bot_update_step, build_config = api.m.chromium_tests.prepare_checkout(
      builder_config, root_solution_revision=revision, report_cache_state=False)

  # Find the matching test targets.
  tests = [
      test for test in build_config.all_tests()
      if test.isolate_target in isolated_targets
  ]

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
          builder_config,
          bot_update_step,
          build_config,
          compile_targets,
          tests_including_triggered=tests[:1],  # Only the first test.
          builder_id=bot_mirror.builder_id,
          override_execution_mode=ctbc.COMPILE_AND_TEST)
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
    # TODO(crbug/1018836): Use distro specific name instead of Linux.
    builders = ctbc.BuilderDatabase.create({
        'chromium.findit': {
            'findit_builder':
                ctbc.BuilderSpec.create(
                    chromium_config='chromium',
                    chromium_apply_config=[
                        'mb',
                    ],
                    gclient_config='chromium',
                    chromium_config_kwargs={
                        'BUILD_CONFIG': 'Release',
                        'TARGET_BITS': 64,
                    },
                    simulation_platform='linux',
                ),
            'findit_tester':
                ctbc.BuilderSpec.create(
                    chromium_config='chromium',
                    chromium_apply_config=['mb'],
                    gclient_config='chromium',
                    chromium_config_kwargs={
                        'BUILD_CONFIG': 'Release',
                        'TARGET_BITS': 64,
                    },
                    execution_mode=ctbc.TEST,
                    parent_buildername='findit_builder',
                    simulation_platform='linux',
                    swarming_dimensions={
                        'os': 'Linux',
                    },
                ),
            'findit_builder_tester':
                ctbc.BuilderSpec.create(
                    chromium_config='chromium',
                    chromium_apply_config=['mb'],
                    gclient_config='chromium',
                    chromium_config_kwargs={
                        'BUILD_CONFIG': 'Release',
                        'TARGET_BITS': 64,
                    },
                    simulation_platform='linux',
                    swarming_dimensions={
                        'os': 'Linux',
                    },
                ),
        },
    })
    return sum([
        api.chromium_tests_builder_config.builder_db(builders),
        api.chromium.ci_build(
            bucket='findit',
            builder='findit_variable',
            builder_group='chromium.findit',
            bot_id='beefy_vm',
        ),
        api.builder_group.for_target('chromium.findit'),
        api.properties(
            target_testername=tester_name,
            revision='r0',
            isolated_targets=isolated_targets,
        ),
        api.platform.name('linux'),
    ], api.empty_test_data())

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

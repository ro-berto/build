# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Compiles with patch and isolates tests"""

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipes.build.chromium.compilator import InputProperties
from PB.recipe_engine import result as result_pb2
from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_tests',
    'chromium_tests_builder_config',
    'filter',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_utils',
]

PROPERTIES = InputProperties


def RunSteps(api, properties):
  with api.chromium.chromium_layout():
    orchestrator = properties.orchestrator.builder_name
    builder_group = properties.orchestrator.builder_group
    orch_builder_id = chromium.BuilderId.create_for_group(
        builder_group, orchestrator)

    _, orch_builder_config = (
        api.chromium_tests_builder_config.lookup_builder(
            builder_id=orch_builder_id))
    api.chromium_tests.configure_build(orch_builder_config)

    api.chromium_tests.report_builders(orch_builder_config)

    raw_result, task = api.chromium_tests.build_affected_targets(
        orch_builder_id, orch_builder_config)

    if raw_result and raw_result.status != common_pb.SUCCESS:
      return raw_result

    tests = task.test_suites
    non_isolated_tests = [t for t in tests if not t.uses_isolate]
    if non_isolated_tests:
      test_runner = api.chromium_tests.create_test_runner(
          non_isolated_tests,
          suffix='with patch',
      )
      with api.chromium_tests.wrap_chromium_tests(orch_builder_config,
                                                  non_isolated_tests):
        raw_result = test_runner()
        if raw_result and raw_result.status != common_pb.SUCCESS:
          return raw_result

    if any(t.uses_isolate for t in tests):
      trigger_properties = {}
      trigger_properties['swarming_command_lines_digest'] = (
          api.chromium_tests.archive_command_lines(
              api.chromium_tests.swarming_command_lines,
              orch_builder_config.isolate_server))
      trigger_properties['swarming_command_lines_cwd'] = (
          api.m.path.relpath(api.m.chromium.output_dir, api.m.path['checkout']))
      trigger_properties['swarm_hashes'] = api.isolate.isolated_tests

      properties_step = api.step('swarming trigger properties', [])
      properties_step.presentation.properties[
          'swarming_trigger_properties'] = trigger_properties
      properties_step.presentation.logs[
          'swarming_trigger_properties'] = api.m.json.dumps(
              trigger_properties, indent=2)

    return raw_result


def GenTests(api):

  def override_test_spec():
    return api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Builder': {
                'scripts': [{
                    "isolate_profile_data": True,
                    "name": "check_static_initializers",
                    "script": "check_static_initializers.py",
                    "swarming": {}
                }],
            },
            'Linux Tests': {
                'gtest_tests': [{
                    'name': 'browser_tests',
                    'swarming': {
                        'can_use_on_swarming_builders': True
                    },
                }],
            },
        })

  yield api.test(
      'basic',
      api.chromium.try_build(builder='linux-rel-compilator'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'))),
      api.filter.suppress_analyze(),
      override_test_spec(),
      api.post_process(post_process.StepTextContains, 'report builders', [
          "running tester 'Linux Tests' on group 'chromium.linux' against "
          "builder 'Linux Builder' on group 'chromium.linux'"
      ]),
      api.post_process(post_process.MustRun, 'compile (with patch)'),
      api.post_process(post_process.MustRun, 'isolate tests (with patch)'),
      api.post_process(post_process.MustRun, 'swarming trigger properties'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_compile_no_isolate',
      api.chromium.try_build(builder='linux-rel-compilator'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'))),
      override_test_spec(),
      api.post_process(post_process.StepTextContains, 'report builders', [
          'tester \'Linux Tests\' on group \'chromium.linux\'',
          'builder \'Linux Builder\' on group \'chromium.linux\''
      ]),
      api.post_process(post_process.DoesNotRun, 'compile (with patch)'),
      api.post_process(post_process.DoesNotRun, 'isolate tests (with patch)'),
      api.post_process(post_process.DoesNotRun, 'swarming trigger properties'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'compile_failed',
      api.chromium.try_build(builder='linux-rel-compilator'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'))),
      override_test_spec(),
      api.filter.suppress_analyze(),
      api.override_step_data('compile (with patch)', retcode=1),
      api.post_process(post_process.StepTextContains, 'report builders', [
          'tester \'Linux Tests\' on group \'chromium.linux\'',
          'builder \'Linux Builder\' on group \'chromium.linux\''
      ]),
      api.post_process(post_process.DoesNotRun, 'isolate tests (with patch)'),
      api.post_process(post_process.DoesNotRun, 'swarming trigger properties'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failing_local_test',
      api.chromium.try_build(builder='linux-rel-compilator'),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='linux-rel-orchestrator',
                  builder_group='tryserver.chromium.linux'))),
      override_test_spec(),
      api.filter.suppress_analyze(),
      api.override_step_data('check_static_initializers (with patch)',
                             api.test_utils.canned_gtest_output(False)),
      api.post_process(post_process.StepTextContains, 'report builders', [
          'tester \'Linux Tests\' on group \'chromium.linux\'',
          'builder \'Linux Builder\' on group \'chromium.linux\''
      ]),
      api.post_process(post_process.DoesNotRun, 'swarming trigger properties'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

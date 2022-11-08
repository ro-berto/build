# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.recipes.build.chromium.compilator import InputProperties

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build.chromium_tests.api import (
    ALL_TEST_BINARIES_ISOLATE_NAME)

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'filter',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/properties',
]

PROPERTIES = InputProperties


def RunSteps(api, properties):
  orchestrator = properties.orchestrator.builder_name
  builder_group = properties.orchestrator.builder_group
  orch_builder_id = chromium.BuilderId.create_for_group(builder_group,
                                                        orchestrator)

  orch_builder_id = chromium.BuilderId.create_for_group(builder_group,
                                                        orchestrator)

  _, orch_builder_config = (
      api.chromium_tests_builder_config.lookup_builder(
          builder_id=orch_builder_id))
  api.chromium_tests.configure_build(orch_builder_config)

  api.chromium_tests.build_affected_targets(
      orch_builder_id,
      orch_builder_config,
      isolate_output_files_for_coverage=True,
      additional_compile_targets=['infra_orchestrator:orchestrator_all'])


def GenTests(api):
  ctbc_api = api.chromium_tests_builder_config

  def ctbc_properties():
    return ctbc_api.properties(
        ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
            builder_group='fake-group',
            builder='fake-builder',
        ).with_mirrored_tester(
            builder_group='fake-group',
            builder='fake-tester',
        ).assemble())

  yield api.test(
      'compilator_isolates_all_tests',
      api.code_coverage(use_clang_coverage=True),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
      ),
      ctbc_properties(),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'scripts': [{
                      "isolate_profile_data": True,
                      "name": "check_static_initializers",
                      "script": "check_static_initializers.py",
                      "swarming": {}
                  }],
              },
              'fake-tester': {
                  'gtest_tests': [{
                      'name': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  }],
              },
          }),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      api.path.exists(api.path['checkout'].join('out/Release/browser_tests')),
      api.post_process(
          post_process.StepCommandContains,
          'compile (with patch)',
          ['browser_tests', 'infra_orchestrator:orchestrator_all'],
      ),
      api.post_process(post_process.MustRun, 'isolate tests (with patch)'),
      api.post_process(post_process.LogContains, 'isolate tests (with patch)',
                       'json.output', [ALL_TEST_BINARIES_ISOLATE_NAME]),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_compile_with_additional_compile_targets_kwarg',
      api.code_coverage(use_clang_coverage=True),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-compilator',
      ),
      ctbc_properties(),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'scripts': [{
                      "isolate_profile_data": True,
                      "name": "check_static_initializers",
                      "script": "check_static_initializers.py",
                      "swarming": {}
                  }],
              },
              'fake-tester': {
                  'gtest_tests': [{
                      'name': 'browser_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  }],
              },
          }),
      api.filter.no_dependency(),
      api.properties(
          InputProperties(
              orchestrator=InputProperties.Orchestrator(
                  builder_name='fake-orchestrator',
                  builder_group='fake-try-group'))),
      api.post_process(post_process.DoesNotRun, 'compile (with patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

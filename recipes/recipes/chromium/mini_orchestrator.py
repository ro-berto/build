# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Analyzes patch and triggers warmed compile builder if needed."""

from RECIPE_MODULES.build import chromium
from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_checkout',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/swarming',
]


def RunSteps(api):
  builder_to_trigger = api.properties['builder_to_trigger']
  builder_id = chromium.BuilderId.create_for_group(
      builder_to_trigger['builder_group'], builder_to_trigger['buildername'])
  with api.chromium.chromium_layout():
    _, builder_config = (
        api.chromium_tests_builder_config.lookup_builder(builder_id=builder_id))

    api.chromium_tests.report_builders(builder_config)

    api.chromium_tests.configure_build(builder_config)
    _, build_config = api.chromium_tests.prepare_checkout(
        builder_config, timeout=3600, add_blamelists=True)

    affected_files = api.chromium_checkout.get_files_affected_by_patch(
        report_via_property=True)

    _, compile_targets = api.chromium_tests.determine_compilation_targets(
        builder_id, builder_config, affected_files, build_config)

    if compile_targets:
      request = api.buildbucket.schedule_request(
          builder=builder_to_trigger['buildername'])
      api.buildbucket.schedule([request])
    return


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.try_build(builder='mini-orchestrator'),
      api.properties(
          builder_to_trigger={
              'builder_group': 'tryserver.chromium.linux',
              'buildername': 'linux-warmed',
          }),
      api.override_step_data(
          'analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['browser_tests'],
              'test_targets': []
          })),
      api.post_process(
          post_process.StepTextContains, 'report builders',
          ['running builder \'Linux Builder\' on group \'chromium.linux\'']),
      api.post_process(post_process.MustRun, 'buildbucket.schedule'),
      api.post_process(post_process.StatusSuccess),
  )

  yield api.test(
      'no_compile',
      api.chromium.try_build(builder='mini-orchestrator'),
      api.properties(
          builder_to_trigger={
              'builder_group': 'tryserver.chromium.linux',
              'buildername': 'linux-warmed',
          }),
      api.post_process(
          post_process.StepTextContains, 'report builders',
          ['running builder \'Linux Builder\' on group \'chromium.linux\'']),
      api.post_process(post_process.DoesNotRun, 'buildbucket.schedule'),
      api.post_process(post_process.StatusSuccess),
  )

  yield api.test(
      'no_builder_to_trigger_passed_in',
      api.chromium.try_build(builder='mini-orchestrator'),
      api.expect_exception("KeyError"),
      api.post_process(post_process.DoesNotRun, 'buildbucket.schedule'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non_existent_builder_to_trigger_passed_in',
      api.chromium.try_build(builder='mini-orchestrator'),
      api.properties(
          builder_to_trigger={
              'builder_group': 'tryserver.chromium.linux',
              'buildername': 'linux-non-existent',
          }),
      api.post_process(post_process.DoesNotRun, 'buildbucket.schedule'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

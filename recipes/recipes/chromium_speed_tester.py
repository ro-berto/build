# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/python',
]
NO_SUFFIX = ''

from recipe_engine import post_process
from PB.recipes.build.chromium_speed_tester import InputProperties
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

PROPERTIES = InputProperties

def RunSteps(api, properties):
  with api.chromium.chromium_layout():
    builder_id, builder_config = (
        api.chromium_tests_builder_config.lookup_builder())
    api.chromium_tests.report_builders(builder_config)
    execution_mode = builder_config.execution_mode
    if execution_mode != ctbc.TEST:
      api.python.infra_failing_step(
          'chromium_speed_tester',
          'Unexpected execution mode. Expect: %s, Actual: %s' %
          (ctbc.TEST, execution_mode))
    api.chromium_tests.configure_build(builder_config)
    update_step, build_config = api.chromium_tests.prepare_checkout(
        builder_config, timeout=3600, no_fetch_tags=True)
    api.chromium_tests.lookup_builder_gn_args(builder_id, builder_config)
    tests = build_config.tests_on(builder_id)
    api.chromium_tests.download_command_lines_for_tests(tests, builder_config)
    test_failure_summary = api.chromium_tests.run_tests(builder_id,
                                                        builder_config, tests)

    task_groups = {
        t.get_task(NO_SUFFIX).request.name:
        t.get_task(NO_SUFFIX).collect_cmd_input() for t in tests
    }
    tester_properties = {
        'buildername':
            api.buildbucket.builder_name,
        'buildnumber':
            api.buildbucket.build.number,
        'perf_dashboard_machine_group':
            properties.perf_dashboard_machine_group,
        'got_revision_cp':
            properties.parent_got_revision_cp,
        'got_v8_revision':
            properties.parent_got_v8_revision,
        'got_webrtc_revision':
            properties.parent_got_webrtc_revision
    }
    additional_trigger_properties = {
        'tasks_groups': api.json.dumps(task_groups),
        'tester_properties': api.json.dumps(tester_properties)
    }

    api.chromium_tests.trigger_child_builds(
        builder_id,
        update_step,
        builder_config,
        additional_properties=additional_trigger_properties)
    return test_failure_summary


def GenTests(api):
  yield api.test(
      'tester-coverage',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.perf',
          builder='linux-perf',
          parent_buildername='linux-builder-perf'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'builder-coverage',
      api.chromium_tests_builder_config.ci_build(
          builder_group='chromium.perf', builder='linux-builder-perf'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

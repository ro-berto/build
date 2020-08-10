# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'recipe_engine/json',
]

from recipe_engine import post_process
from PB.recipes.build.chromium_speed_processor import InputProperties
from RECIPE_MODULES.build.chromium_tests import bot_spec

PROPERTIES = InputProperties


def RunSteps(api, properties):
  with api.chromium.chromium_layout():
    # 1. update the bot to have latest scripts
    bot = api.chromium_tests.lookup_bot_metadata(builders=None)
    execution_mode = bot.settings.execution_mode
    if execution_mode != bot_spec.TEST:
      api.python.infra_failing_step(
          'chromium_speed_tester',
          'Unexpected execution mode. Expect: %s, Actual: %s' %
          (bot_spec.TEST, execution_mode))
    api.chromium_tests.configure_build(bot.settings)
    api.chromium_tests.prepare_checkout(
        bot.settings, timeout=3600, no_fetch_tags=True)

    # 2. run collect task for each group
    task_groups = api.json.loads(properties.tasks_groups)
    tester_properties = api.json.loads(properties.tester_properties)

    for group_name, task_ids in task_groups.iteritems():
      collect_task_args = api.chromium_swarming.get_collect_task_args(
          merge_script=api.path['checkout'].join('tools', 'perf',
                                                 'process_perf_results.py'),
          merge_arguments=['--lightweight'],
          build_properties=tester_properties,
          requests_json=task_ids)

      step_result = api.chromium_swarming.run_collect_task_script(
          group_name, collect_task_args, gen_step_test_data=None)

      step_result.presentation.step_text = 'merging...'
      step_result.presentation.logs['Merge script log'] = [
          step_result.raw_io.output
      ]


MOCK_TASK_GROUPS = """
                    {
                      "performance_test_suite":
                      { 
                        "tasks": [ { "task_id": "4b9894c1f295c310" }]
                      }
                    }
                    """
MOCK_PROR_JSON_STRING = """
                        {
                          "builder_name":
                            "linux-perf",
                          "build_number":
                            "666",
                          "perf_dashboard_machine_group":
                            "ChromiumPerfFyi",
                          "got_revision_cp":
                            "refs/heads/master@{#758236}",
                          "got_v8_revision":
                            "0bb2b3008e7530eb4ac3f4c68d328649ff662e30",
                          "got_webrtc_revision":
                            "9f0b36c4610de8e0fe4bde2f57c8bc487e3a1005"
                        }
                        """

def GenTests(api):
  yield api.test(
      'recipe-coverage',
      api.chromium_tests.platform([{
          'mastername': 'chromium.perf',
          'buildername': 'linux-perf',
      }]),
      api.chromium.ci_build(
          mastername='chromium.perf',
          builder='linux-perf',
          parent_buildername='linux-builder-perf'),
      api.properties(
          InputProperties(
              tasks_groups=MOCK_TASK_GROUPS,
              tester_properties=MOCK_PROR_JSON_STRING)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'builder-coverage',
      api.chromium_tests.platform([{
          'mastername': 'chromium.perf',
          'buildername': 'linux-builder-perf'
      }]),
      api.chromium.ci_build(
          mastername='chromium.perf', builder='linux-builder-perf'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

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

PROPERTIES = InputProperties


def RunSteps(api, properties):
  with api.chromium.chromium_layout():
    # 1. update the bot to have latest scripts
    bot = api.chromium_tests.lookup_bot_metadata(builders=None)
    bot_type = bot.settings.bot_type
    if bot_type != 'tester':
      api.python.infra_failing_step(
          'chromium_speed_tester',
          'Unexpected bot type. Expect: tester, Actual: %s' % bot_type)
    api.chromium_tests.configure_build(bot.settings)
    api.chromium_tests.prepare_checkout(
        bot.settings, timeout=3600, no_fetch_tags=True)

    # 2. run collect task for each group
    parent_builder_name = properties.tester_builder_name
    parent_build_number = properties.tester_build_number
    perf_dashboard_machine_group = \
      properties.tester_perf_dashboard_machine_group
    task_groups = api.json.loads(properties.tasks_groups)

    for group_name, group_info in task_groups.iteritems():
      group_info = group_info
      task_properties = group_info['building_prop']
      task_ids = group_info['task_ids']

      # TODO(crbug.com/1077104) Only keep swarming IDs in the dictionary.
      properties = dict(task_properties)
      properties['buildername'] = parent_builder_name
      properties['buildnumber'] = parent_build_number
      properties['perf_dashboard_machine_group'] = perf_dashboard_machine_group

      collect_task_args = api.chromium_swarming.get_collect_task_args(
          merge_script=api.path['checkout'].join('tools', 'perf',
                                                 'process_perf_results.py'),
          merge_arguments=['--lightweight'],
          build_properties=properties,
          requests_json=task_ids)

      step_result = api.chromium_swarming.run_collect_task_script(
          group_name, collect_task_args, gen_step_test_data=None)

      step_result.presentation.step_text = 'merging...'
      step_result.presentation.logs['Merge script log'] = [
          step_result.raw_io.output
      ]


MOCK_PROP_JSON_STRING = """
                        { "building_prop":
                          { "got_angle_revision":
                            "cf2c8e6068c8d009c5ef9ec2d2094d05aa1c1a46",
                            "got_dawn_revision":
                            "ab2c84ffd2a49a97abf4c22b1e88e42f8d02c1ff",
                            "got_nacl_revision":
                            "d304d90ecc17351ce0fdab3e7452052a469c0976",
                            "got_revision":
                            "a7d2f1826c84a08c7fb746cd900f9f9e0fa0cd05",
                            "got_revision_cp":
                            "refs/heads/master@{#758236}",
                            "got_src_internal_revision":
                            "647a242debd9e5254b96aa42211ff406f32e38a6",
                            "got_swarming_client_revision":
                            "cc958279ffd6853e0a1b227a7e957ca334fe56af",
                            "got_swiftshader_revision":
                            "e6f65d9265e764034c1c078bd67db893cd565cac",
                            "got_v8_revision":
                            "0bb2b3008e7530eb4ac3f4c68d328649ff662e30",
                            "got_v8_revision_cp":
                            "refs/heads/8.4.47@{#1}",
                            "got_webrtc_revision":
                            "9f0b36c4610de8e0fe4bde2f57c8bc487e3a1005",
                            "got_webrtc_revision_cp":
                            "refs/heads/master@{#31046}" },
                          "task_ids":
                          { "tasks": [ { "task_id": "4b9894c1f295c310" }]}}
                        """
MOCK_TASK_GROUPS = '{"performance_test_suite": ' + MOCK_PROP_JSON_STRING + '}'


def GenTests(api):
  yield (api.test(
      'recipe-coverage',
      api.chromium_tests.platform([{
          'mastername': 'chromium.perf',
          'buildername': 'linux-perf',
      }]),
      api.chromium.ci_build(
          mastername='chromium.perf',
          builder='linux-perf',
          parent_buildername='linux-builder-perf'),
  ) + api.properties(
      InputProperties(
          tasks_groups=MOCK_TASK_GROUPS,
          tester_builder_name='linux-perf',
          tester_build_number=666,
          tester_perf_dashboard_machine_group='ChromiumPerfFyi')) +
         api.post_process(post_process.StatusSuccess) + api.post_process(
             post_process.DropExpectation))

  yield (api.test(
      'builder-coverage',
      api.chromium_tests.platform([{
          'mastername': 'chromium.perf',
          'buildername': 'linux-builder-perf'
      }]),
      api.chromium.ci_build(
          mastername='chromium.perf', builder='linux-builder-perf')) +
         api.post_process(post_process.StatusException) + api.post_process(
             post_process.DropExpectation))

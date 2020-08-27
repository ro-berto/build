# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/python',
]
NO_SUFFIX = ''

from recipe_engine import post_process
from PB.recipes.build.chromium_speed_tester import InputProperties
from RECIPE_MODULES.build.chromium_tests import bot_spec

PROPERTIES = InputProperties

def RunSteps(api, properties):
  with api.chromium.chromium_layout():
    bot = api.chromium_tests.lookup_bot_metadata(builders=None)
    execution_mode = bot.settings.execution_mode
    if execution_mode != bot_spec.TEST:
      api.python.infra_failing_step(
          'chromium_speed_tester',
          'Unexpected execution mode. Expect: %s, Actual: %s' %
          (bot_spec.TEST, execution_mode))
    api.chromium_tests.configure_build(bot.settings)
    update_step, build_config = api.chromium_tests.prepare_checkout(
        bot.settings, timeout=3600, no_fetch_tags=True)
    api.chromium_tests.lookup_builder_gn_args(bot)
    tests = build_config.tests_on(bot.builder_id)
    api.chromium_tests.download_command_lines_for_tests(tests, bot.settings)
    test_failure_summary = api.chromium_tests.run_tests(bot, tests)

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
        bot.builder_id,
        update_step,
        bot.settings,
        additional_properties=additional_trigger_properties)
    return test_failure_summary


def GenTests(api):
  yield api.test(
      'tester-coverage',
      api.chromium_tests.platform([{
          'builder_group': 'chromium.perf',
          'buildername': 'linux-perf'
      }]),
      api.chromium.ci_build(
          builder_group='chromium.perf',
          builder='linux-perf',
          parent_buildername='linux-builder-perf'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'builder-coverage',
      api.chromium_tests.platform([{
          'builder_group': 'chromium.perf',
          'buildername': 'linux-builder-perf'
      }]),
      api.chromium.ci_build(
          builder_group='chromium.perf', builder='linux-builder-perf'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

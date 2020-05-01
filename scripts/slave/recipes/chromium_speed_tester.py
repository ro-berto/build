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

PROPERTIES = InputProperties


def _debug_lines(bot, tests, task_groups):
  debug_lines = []
  debug_lines.append('bot.builder_id: %s' % bot.builder_id)
  debug_lines += ['test name: %s' % t.name for t in tests]
  debug_lines += [' == task IDs ==']
  debug_lines += [
      'group: %s <br/> tasks: %s' % (k, v) for k, v in task_groups.iteritems()
  ]
  debug_lines += [' == building prop ==']
  debug_lines += [
      'test: %s <br/> prop: %s' %
      (t.name, t.get_task(NO_SUFFIX).build_properties) for t in tests
  ]
  debug_lines += [' == task output dir ==']
  debug_lines += [
      'test: %s <br/> dir: %s' % (t.name, t.get_task(NO_SUFFIX).task_output_dir)
      for t in tests
  ]
  return debug_lines


def RunSteps(api, properties):
  with api.chromium.chromium_layout():
    bot = api.chromium_tests.lookup_bot_metadata(builders=None)
    bot_type = bot.settings.bot_type
    if bot_type != 'tester':
      api.python.infra_failing_step(
          'chromium_speed_tester',
          'Unexpected bot type. Expect: tester, Actual: %s' % bot_type)
    api.chromium_tests.configure_build(bot.settings)
    update_step, build_config = api.chromium_tests.prepare_checkout(
        bot.settings, timeout=3600, no_fetch_tags=True)
    api.chromium_tests.lookup_builder_gn_args(bot)
    tests = build_config.tests_on(bot.builder_id)
    test_failure_summary = api.chromium_tests.run_tests(bot, tests)
    task_groups = {
        t.get_task(NO_SUFFIX).request.name: {
            'task_ids': t.get_task(NO_SUFFIX).collect_cmd_input(),
            'building_prop': t.get_task(NO_SUFFIX).build_properties,
            'task_output_dir': t.get_task(NO_SUFFIX).task_output_dir
        } for t in tests
    }
    additional_trigger_properties = {
        'tasks_groups':
            api.json.dumps(task_groups),
        'tester_builder_name':
            api.buildbucket.builder_name,
        'tester_build_number':
            api.buildbucket.build.number,
        'tester_perf_dashboard_machine_group':
            properties.perf_dashboard_machine_group
    }
    api.python.succeeding_step(
        'Debug info', '<br/>'.join(_debug_lines(bot, tests, task_groups)))
    api.chromium_tests.trigger_child_builds(
        bot.builder_id,
        update_step,
        bot.settings,
        additional_properties=additional_trigger_properties)
    return test_failure_summary


def GenTests(api):
  yield (api.test(
      'tester-coverage',
      api.chromium_tests.platform([{
          'mastername': 'chromium.perf',
          'buildername': 'linux-perf'
      }]),
      api.chromium.ci_build(
          mastername='chromium.perf',
          builder='linux-perf',
          parent_buildername='linux-builder-perf')) + api.post_process(
              post_process.StatusSuccess) + api.post_process(
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

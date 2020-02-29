# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'recipe_engine/python',
]

from recipe_engine import post_process


def RunSteps(api):
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
    test_failure_summary = api.chromium_tests.run_tests(bot, build_config)
    api.chromium_tests.trigger_child_builds(bot.builder_id, update_step,
                                            build_config)
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

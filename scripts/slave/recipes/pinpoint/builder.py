# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_tests',
  'recipe_engine/json',
  'recipe_engine/properties',
]


def RunSteps(api):
  with api.chromium.chromium_layout():
    mastername = api.properties.get('mastername')
    buildername = api.properties.get('buildername')

    bot = api.chromium_tests.trybots[mastername]['builders'][buildername]
    bot_config = api.chromium_tests.create_bot_config_object(bot['bot_ids'])

    api.chromium_tests.configure_build(bot_config)
    update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config)
    test_config = api.chromium_tests.get_tests(bot_config, bot_db)
    compile_targets = api.chromium_tests.get_compile_targets(
        bot_config, bot_db, test_config.all_tests())
    api.chromium_tests.compile_specific_targets(
        bot_config, update_step, bot_db,
        compile_targets, test_config.all_tests())


def GenTests(api):
  yield (
    api.test('basic') +
    api.properties.generic(mastername='tryserver.chromium.perf',
                           buildername='Android Compile Perf') +
    api.chromium_tests.read_source_side_spec(
        'chromium.perf', {
            'Android One Perf': {
                'isolated_scripts': [
                    {
                        'isolate_name': 'telemetry_perf_tests',
                        'name': 'benchmark',
                    },
                ],
            },
        })
  )

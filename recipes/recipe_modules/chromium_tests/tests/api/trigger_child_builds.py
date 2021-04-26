# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from PB.recipe_modules.recipe_engine.led import properties as led_properties_pb

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  api.chromium_tests.configure_build(builder_config)
  update_step, _ = api.chromium_tests.prepare_checkout(builder_config)
  api.chromium_tests.trigger_child_builds(builder_id, update_step,
                                          builder_config)


def GenTests(api):

  def builder_with_tester_to_trigger():
    return api.chromium_tests_builder_config.ci_build(
        builder_group='fake-group',
        builder='fake-builder',
        builder_db=ctbc.BuilderDatabase.create({
            'fake-group': {
                'fake-builder':
                    ctbc.BuilderSpec.create(
                        chromium_config='chromium',
                        gclient_config='chromium',
                    ),
                'fake-tester':
                    ctbc.BuilderSpec.create(
                        execution_mode=ctbc.TEST,
                        chromium_config='chromium',
                        gclient_config='chromium',
                        parent_buildername='fake-builder',
                    )
            }
        }))

  yield api.test(
      'scheduler',
      builder_with_tester_to_trigger(),
      api.post_check(post_process.StatusSuccess),
  )

  led_properties = led_properties_pb.InputProperties()
  led_properties.led_run_id = 'fake-id'
  yield api.test(
      'led',
      builder_with_tester_to_trigger(),
      api.properties(
          **{
              '$recipe_engine/led': {
                  'led_run_id': 'fake-run-id',
                  'isolated_input': {
                      'hash': 'fake-hash',
                  },
              },
          }),
      api.post_check(post_process.StatusSuccess),
  )

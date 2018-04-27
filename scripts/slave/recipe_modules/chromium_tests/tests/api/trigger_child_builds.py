# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium_tests',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
]


def RunSteps(api):
  bot_config = api.chromium_tests.create_bot_config_object(
      api.properties['mastername'], api.properties['buildername'])
  api.chromium_tests.configure_build(bot_config)
  update_step, bot_db = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.trigger_child_builds(
      api.properties['mastername'], api.properties['buildername'],
      update_step, bot_db)


def GenTests(api):
  def trigger_includes_bucket(check, steps_odict, builder=None, bucket=None):
    for trigger_spec in steps_odict['trigger']['trigger_specs']:
      if trigger_spec['builder_name'] == builder:
        check(trigger_spec['bucket'] == bucket)
    return steps_odict

  yield (
      api.test('cross_master_trigger') +
      api.platform.name('linux') +
      api.properties.generic(
          mastername='chromium.android',
          buildername='Android arm Builder (dbg)') +
      api.post_process(post_process.StatusCodeIn, 0) +
      api.post_process(trigger_includes_bucket,
                       builder='Lollipop Low-end Tester',
                       bucket='master.chromium.android.fyi') +
      api.post_process(post_process.DropExpectation)
  )

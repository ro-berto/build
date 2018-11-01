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

CUSTOM_BUILDERS = {
  'chromium.example': {
    'settings': {
      'build_gs_bucket': 'chromium-example-archive',
    },
    'builders': {
      'Fake Builder': {
        'chromium_config': 'android',
        'chromium_apply_config': [
          'download_vr_test_apks',
        ],
        'gclient_config': 'chromium',
        'gclient_apply_config': ['android'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'android_config': 'main_builder_mb',
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'chromium.example2': {
    'settings': {
      'build_gs_bucket': 'chromium-example-archive',
    },
    'builders': {
      'Fake Tester': {
        'chromium_config': 'android',
        'gclient_config': 'chromium',
        'gclient_apply_config': ['android'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
        },
        'parent_buildername': 'Fake Builder',
        'parent_mastername': 'chromium.example',
        'bot_type': 'tester',
        'android_config': 'main_builder_mb',
        'android_apply_config': ['use_devil_provision'],
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
}

def RunSteps(api):
  bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(
          api.properties['mastername'], api.properties['buildername'])],
      builders=CUSTOM_BUILDERS)
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
          buildername='Fake Builder',
          mastername='chromium.example',
          parent_buildername='Android arm Builder (dbg)',
          parent_mastername='chromium.android') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(trigger_includes_bucket,
                       builder='Fake Tester',
                       bucket='master.chromium.example2') +
      api.post_process(post_process.DropExpectation)
  )

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/json',
    'recipe_engine/platform',
]

CUSTOM_BUILDERS = {
    'chromium.example': {
        'builders': {
            'Fake Builder': {
                'build_gs_bucket': 'chromium-example-archive',
                'chromium_config': 'android',
                'chromium_apply_config': ['download_vr_test_apks',],
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
        'builders': {
            'Fake Tester': {
                'build_gs_bucket': 'chromium-example-archive',
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
  builder_id = api.chromium.get_builder_id()
  bot_config = api.chromium_tests.create_bot_config_object(
      [builder_id], builders=CUSTOM_BUILDERS)
  api.chromium_tests.configure_build(bot_config)
  update_step, _ = api.chromium_tests.prepare_checkout(bot_config)
  api.chromium_tests.trigger_child_builds(builder_id, update_step, bot_config)


def GenTests(api):
  def trigger_includes_bucket(check, steps_odict, builder=None):
    batches = [
      b['jobs'] for b in api.json.loads(steps_odict['trigger'].stdin)['batches']
    ]
    check(any(j['job'] == builder for jobs in batches for j in jobs))
    return steps_odict

  yield api.test(
      'cross_master_trigger',
      api.platform.name('linux'),
      api.chromium.ci_build(
          builder='Fake Builder',
          mastername='chromium.example',
          parent_buildername='Android arm Builder (dbg)',
          parent_mastername='chromium.android'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(trigger_includes_bucket, builder='Fake Tester'),
      api.post_process(post_process.DropExpectation),
  )

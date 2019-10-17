# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from recipe_engine.recipe_api import Property
from recipe_engine.types import freeze

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'chromium_android',
  'emulator',
  'depot_tools/gclient',
  'recipe_engine/buildbucket',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'
BUILDERS = freeze({
    'chromium.fyi': {
        'Disable settings after launch emulator': {
            'config': 'x86_builder',
            'target': 'Debug',
            'abi': 'x86',
            'api_level': 23,
            'partition_size': '1024M',
            'sdcard_size': '512M',
            'provision_settings': {
                'disable_location': True,
                'disable_network': True,
            },
            'sample_gtest_suite': 'sample_test',
        }
    }
})

PROPERTIES = {
  'mastername': Property(),
}

def RunSteps(api, mastername):
  builder = BUILDERS[mastername][api.buildbucket.builder_name]
  api.chromium_android.configure_from_properties(
      builder['config'],
      REPO_NAME='src',
      REPO_URL=REPO_URL,
      INTERNAL=False,
      BUILD_CONFIG=builder['target'])
  api.chromium_android.apply_config('remove_all_system_webviews')

  api.emulator.set_config('base_config')
  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')

  api.bot_update.ensure_checkout()
  api.chromium.ensure_goma()
  api.chromium.runhooks()

  api.emulator.install_emulator_deps(api_level=builder.get('api_level'))

  provision_settings = builder.get('provision_provision_settings', {})

  with api.emulator.launch_emulator(
      abi=builder.get('abi'),
      api_level=builder.get('api_level'),
      amount=builder.get('amount', 1),
      partition_size=builder.get('partition_size'),
      sdcard_size=builder.get('sdcard_size')):
    api.emulator.wait_for_emulator(num=1)
    suite = builder.get('sample_gtest_suite')
    api.chromium_android.provision_devices(emulators=True, **provision_settings)
    api.chromium_android.run_test_suite(suite)

def GenTests(api):
  sanitize = lambda s: ''.join(c if c.isalnum() else '_' for c in s)

  for mastername in BUILDERS:
    master = BUILDERS[mastername]
    for buildername in master:
      yield api.test(
          '%s_test_basic' % sanitize(buildername),
          api.buildbucket.generic_build(builder=buildername),
          api.properties(mastername=mastername),
      )

# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from recipe_engine.recipe_api import Property
from recipe_engine.types import freeze

DEPS = [
  'blimp',
  'chromium',
  'chromium_android',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/path',
  'recipe_engine/properties',
]

BUILDERS = freeze({
  'chromium.fyi': {
    'Blimp Client Engine Integration': {
      'chromium_config': 'android',
      'config': 'main_builder',
      'gclient_apply_config': 'android',
      'gclient_config': 'chromium',
      'target': 'Debug',
    },
  },
})

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

def RunSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  builder = BUILDERS[mastername][buildername]
  api.chromium.set_config('chromium')
  api.chromium_android.configure_from_properties(
      builder['config'],
      REPO_NAME='src',
      REPO_URL=REPO_URL,
      INTERNAL=False,
      BUILD_CONFIG=builder['target'])

  api.gclient.set_config(builder['gclient_config'])
  api.gclient.apply_config(builder['gclient_apply_config'])
  api.blimp.set_config('base_config')
  api.bot_update.ensure_checkout()
  api.chromium.ensure_goma()
  api.chromium_android.clean_local_files()
  api.chromium.runhooks()

  android_build = api.path['checkout'].join('out-android')
  linux_build = api.path['checkout'].join('out-linux')
  android_debug_dir = android_build.join(api.chromium.c.build_config_fs)
  linux_debug_dir = linux_build.join(api.chromium.c.build_config_fs)

  api.chromium.run_mb(mastername=mastername,
                      buildername=buildername,
                      build_dir=linux_debug_dir,
                      phase='engine')
  api.chromium.compile(targets=['blimp'],
                       out_dir=linux_build,
                       use_goma_module=True)
  api.chromium.run_mb(mastername=mastername,
                      buildername=buildername,
                      build_dir=android_debug_dir,
                      phase='client')
  api.chromium.compile(targets=['blimp', 'chrome_public_apk'],
                       out_dir=android_build,
                       use_goma_module=True)

  apk_path = android_debug_dir.join('apks', 'ChromePublic.apk')

  with api.blimp.engine_forwarder(output_linux_dir=linux_debug_dir):
    api.blimp.load_client(output_linux_dir=linux_debug_dir,
                          apk_path=apk_path)

def GenTests(api):
  sanitize = lambda s: ''.join(c if c.isalnum() else '_' for c in s)

  yield (
      api.test('%s_test_pass' % sanitize('Blimp Client Engine Integration')) +
      api.properties.generic(
        buildername='Blimp Client Engine Integration',
        mastername='chromium.fyi')
  )

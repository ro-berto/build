# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from infra.libs.infra_types import freeze, thaw

DEPS = [
    'auto_bisect',
    'bot_update',
    'chromium',
    'chromium_android',
    'gclient',
    'path',
    'properties',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

BUILDERS = freeze({
  'tryserver.chromium.perf': {
    'android_one_perf_bisect': {
      'recipe_config': 'perf',
    },
    'android_nexus4_perf_bisect': {
      'recipe_config': 'perf',
    },
    'android_nexus5_perf_bisect': {
      'recipe_config': 'perf',
    },
    'android_nexus6_perf_bisect': {
      'recipe_config': 'perf',
    },
    'android_nexus7_perf_bisect': {
      'recipe_config': 'perf',
    },
    'android_nexus9_perf_bisect': {
      'recipe_config': 'perf',
    },
  },
})

def RunSteps(api):
  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  bot_config = BUILDERS[mastername][buildername]
  # The following lines configures android bisect bot to to checkout codes,
  # executes runhooks, provisions devices and runs legacy bisect script.
  recipe_config = bot_config.get('recipe_config', 'perf')
  kwargs = {
    'REPO_NAME': 'src',
    'REPO_URL': REPO_URL,
    'INTERNAL': False,
    'BUILD_CONFIG': 'Release',
    'TARGET_PLATFORM': 'android',
  }

  api.chromium_android.set_config(
      recipe_config, **kwargs)
  api.gclient.set_config(recipe_config, **kwargs)
  api.chromium.set_config(recipe_config, **kwargs)
  api.gclient.apply_config('android')

  api.bot_update.ensure_checkout()
  api.chromium_android.clean_local_files()
  api.chromium_android.common_tests_setup_steps(perf_setup=True)
  api.chromium.runhooks()
  api.auto_bisect.run_bisect_script()

def GenTests(api):
  for mastername, master_dict in BUILDERS.items():
    for buildername in master_dict:
      yield (api.test('basic_' + buildername)
      +api.properties.tryserver(
          mastername=mastername,
          buildername=buildername))

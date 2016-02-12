# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'file',
  'gsutil',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]


BUILDERS = freeze({
  'tryserver.chromium.linux': {
    'builders': {
      'linux_chromium_clang_upload': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },

        # We need this to build the Clang toolchain
        # with proper AddressSanitizer prebuilts for
        # Chrome on Android.
        'gclient_apply_config': ['android'],
      },
    },
  },
})


def RunSteps(api):
  mastername = api.m.properties['mastername']
  buildername, bot_config = api.chromium.configure_bot(BUILDERS, ['mb'])

  api.bot_update.ensure_checkout(
      force=True, patch_root=bot_config.get('root_override'))

  api.chromium.runhooks()

  api.chromium.run_mb(mastername, buildername)

  api.python(
      'package clang',
      api.path['checkout'].join('tools', 'clang', 'scripts', 'package.py'))


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
from recipe_engine.types import freeze

DEPS = [
  'archive',
  'depot_tools/bot_update',
  'chromium',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]


BUILDERS = freeze({
  'chromium.fyi': {
    'builders': {
      'ClangToTLinuxASanLibfuzzer': {
        'chromium_config': 'chromium_clang',
        'chromium_apply_config': [ 'clang_tot', 'proprietary_codecs' ],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
      },
    },
  },
})


def RunSteps(api):
  mastername = api.m.properties['mastername']
  buildername, bot_config = api.chromium.configure_bot(BUILDERS, ['mb'])

  api.bot_update.ensure_checkout(
      patch_root=bot_config.get('root_override'))

  api.chromium.ensure_goma()
  api.chromium.runhooks()
  api.chromium.mb_gen(mastername, buildername, use_goma=False)

  api.chromium.compile(targets=['empty_fuzzer'],
                       use_goma_module=True)

  config_kwargs = bot_config.get('chromium_config_kwargs', dict())
  build_config = config_kwargs.get('BUILD_CONFIG', 'Release')
  build_dir=api.path['start_dir'].join('src', 'out', build_config)

  api.step('running empty_fuzzer', [api.path.join(build_dir, 'empty_fuzzer'),
                                    '-runs=1'])


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

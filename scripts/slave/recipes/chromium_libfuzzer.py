# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'bot_update',
  'chromium',
  'file',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


BUILDERS = freeze({
  'chromium.fyi': {
    'builders': {
      'Libfuzzer Upload Linux': {
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
      force=True, patch_root=bot_config.get('root_override'))

  api.chromium.runhooks()

  api.chromium.run_mb(mastername, buildername)

  api.chromium.compile(targets=['gn', 'gn_unittests'], force_clobber=True)

  path_to_binary = str(api.path['checkout'].join('out', 'Release', 'gn'))

  api.step('gn version', [path_to_binary, '--version'])

  api.chromium.runtest('gn_unittests')


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

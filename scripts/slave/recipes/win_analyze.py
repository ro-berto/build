# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'chromium',
]


BUILDERS = {
  'chromium.fyi': {
    'builders': {
      'Chromium Windows Analyze': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
        'chromium_apply_config': ['clobber'],
      },
    },
  },
}


def RunSteps(api):
  api.chromium.configure_bot(BUILDERS, ['win_analyze', 'mb'])

  api.bot_update.ensure_checkout()

  api.chromium.ensure_goma()
  api.chromium.runhooks()

  # This is needed to disable building with goma
  api.chromium.c.compile_py.compiler = None
  api.chromium.c.compile_py.goma_dir = None

  api.chromium.mb_gen('chromium.fyi', 'Chromium Windows Analyze',
                      use_goma=False)

  api.chromium.compile(targets=['chrome'])


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

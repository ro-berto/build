# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
]


BUILDERS = {
  'chromium.mojo': {
    'builders': {
      'Chromium Mojo Linux': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
        },
      },
    },
  },
}


def GenSteps(api):
  _, bot_config = api.chromium.configure_bot(BUILDERS, ['gn'])

  api.bot_update.ensure_checkout(force=True,
                                 patch_root=bot_config.get('root_override'))

  api.chromium.runhooks()

  api.chromium.run_gn(use_goma=True)

  api.chromium.compile(targets=['html_viewer_unittests'])

  api.chromium.runtest('html_viewer_unittests')


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

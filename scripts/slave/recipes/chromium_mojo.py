# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from infra.libs.infra_types import freeze

DEPS = [
  'bot_update',
  'chromium',
  'path',
  'python',
]


BUILDERS = freeze({
  'chromium.mojo': {
    'builders': {
      'Chromium Mojo Linux': {
        'chromium_apply_config': ['gn_use_prebuilt_mojo_shell'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
        },
      },
    },
  },
})

def _RunApptests(api):
  apptest_runner = api.path['checkout'].join('mojo', 'tools',
      'apptest_runner.py')
  apptest_config = api.path['checkout'].join('mojo', 'tools',
      'data', 'apptests')
  api.python('run apptests', apptest_runner,
             [apptest_config, api.chromium.output_dir])


def GenSteps(api):
  _, bot_config = api.chromium.configure_bot(BUILDERS, ['gn'])

  api.bot_update.ensure_checkout(force=True,
                                 patch_root=bot_config.get('root_override'))

  api.chromium.runhooks()

  api.chromium.run_gn(use_goma=True)

  api.chromium.compile(targets=['html_viewer_unittests',
                                'mojo/services/network',
                                'mojo/services/network:apptests'])

  api.chromium.runtest('html_viewer_unittests')

  _RunApptests(api)


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from infra.libs.infra_types import freeze
from slave import recipe_api

DEPS = [
  'bot_update',
  'chromium',
  'path',
  'properties',
  'python',
  'step',
]


BUILDERS = freeze({
  'chromium.mojo': {
    'builders': {
      'Chromium Mojo Linux': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
        },
      },
      'Chromium Mojo Android': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
        },
      },
    },
  },
})


@recipe_api.composite_step
def _RunApptests(api):
  runner = api.path['checkout'].join('mojo', 'tools', 'apptest_runner.py')
  tests = api.path['checkout'].join('mojo', 'tools', 'data', 'apptests')
  api.python('app_tests', runner, [tests, api.chromium.output_dir])


def GenSteps(api):
  _, bot_config = api.chromium.configure_bot(BUILDERS, ['gn'])
  is_android = 'Android' in api.properties.get('buildername')

  api.bot_update.ensure_checkout(force=True,
                                 patch_root=bot_config.get('root_override'))

  api.chromium.runhooks()

  api.chromium.run_gn(use_goma=True)

  api.chromium.compile(targets=['html_viewer_unittests',
                                'mojo/services/network',
                                'mojo/services/network:apptests'])

  with api.step.defer_results():
    api.chromium.runtest('html_viewer_unittests')
    if not is_android:
      _RunApptests(api)


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

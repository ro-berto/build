# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from infra.libs.infra_types import freeze
from recipe_engine import recipe_api

DEPS = [
  'bot_update',
  'chromium',
  'chromium_android',
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
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
    },
  },
})


@recipe_api.composite_step
def _RunApptests(api):
  runner = api.path['checkout'].join('mojo', 'tools', 'apptest_runner.py')
  tests = api.path['checkout'].join('mojo', 'tools', 'data', 'apptests')
  api.python('app_tests', runner, [tests, api.chromium.output_dir, '--verbose'])


def GenSteps(api):
  api.chromium.configure_bot(BUILDERS, ['gn'])

  api.bot_update.ensure_checkout(force=True)

  api.chromium.runhooks()

  api.chromium.run_gn(use_goma=True)

  api.chromium.compile(targets=['mandoline:all'])

  if api.chromium.c.TARGET_PLATFORM == 'android':
    api.chromium_android.detect_and_setup_devices()

  with api.step.defer_results():
    api.chromium.runtest('html_viewer_unittests')
    api.chromium.runtest('mojo_common_unittests')
    api.chromium.runtest('mojo_runner_unittests')
    api.chromium.runtest('mojo_shell_unittests')
    api.chromium.runtest('mojo_surfaces_lib_unittests')
    api.chromium.runtest('resource_provider_unittests')
    api.chromium.runtest('view_manager_unittests')
    _RunApptests(api)


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

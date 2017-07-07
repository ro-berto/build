# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gsutil',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]


BUILDERS = freeze({
  'tryserver.chromium.linux': {
    'builders': {
      'linux_chromium_gn_upload': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['clobber'],

        # We need this to pull the Linux sysroots.
        'gclient_apply_config': ['chrome_internal'],
      },
    },
  },
  'tryserver.chromium.mac': {
    'builders': {
      'mac_chromium_gn_upload': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'mac',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['clobber'],
      },
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win8_chromium_gn_upload': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
        'chromium_apply_config': ['clobber'],
      },
    },
  },
})


def RunSteps(api):
  mastername = api.m.properties['mastername']
  buildername, bot_config = api.chromium.configure_bot(BUILDERS,
                                                       ['gn_for_uploads', 'mb'])

  api.bot_update.ensure_checkout(
      patch_root=bot_config.get('root_override'))

  api.chromium.ensure_goma()

  api.chromium.runhooks()

  api.chromium.run_mb(mastername, buildername)

  api.chromium.compile(targets=['gn', 'gn_unittests'], use_goma_module=True)

  path_to_binary = str(api.path['checkout'].join('out', 'Release', 'gn'))
  if api.platform.is_win:
    path_to_binary += '.exe'

  api.step('gn version', [path_to_binary, '--version'])

  api.chromium.runtest('gn_unittests')

  if not api.platform.is_win:
    api.m.step('gn strip', cmd=['strip', path_to_binary])

  api.python('upload',
             api.depot_tools.upload_to_google_storage_path,
             ['-b', 'chromium-gn', path_to_binary])

  sha1 = api.file.read_text('gn sha1', path_to_binary + '.sha1',
                            test_data='0123456789abcdeffedcba987654321012345678')
  api.step.active_result.presentation.step_text = sha1


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

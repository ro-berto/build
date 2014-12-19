# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'file',
  'gsutil',
  'path',
  'platform',
  'properties',
  'step',
]


BUILDERS = {
  'tryserver.chromium.linux': {
    'builders': {
      'linux_chromium_gn_upload_x64': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },

        # We need this to pull the Linux sysroots.
        'gclient_apply_config': ['chrome_internal'],
      },
      'linux_chromium_gn_upload_x86': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 32,
        },

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
      },
    },
  },
}


def GenSteps(api):
  _, bot_config = api.chromium.configure_bot(BUILDERS, ['gn_for_uploads'])

  api.bot_update.ensure_checkout(
      force=True, patch_root=bot_config.get('root_override'))

  # We need to explicitly pass in the GYP_DEFINES in an environment
  # since we do not normally set it when GN is the project generator.
  # (and the GYP_DEFINES need to be set to pull the right sysroots on Linux).
  api.chromium.runhooks(env=api.chromium.c.gyp_env.as_jsonish())

  api.chromium.run_gn()

  api.chromium.compile(targets=['gn', 'gn_unittests'], force_clobber=True)

  path_to_binary = str(api.path['checkout'].join('out', 'Release', 'gn'))
  if api.platform.is_win:
    path_to_binary += '.exe'

  api.step('gn version', [path_to_binary, '--version'])

  # TODO: crbug.com/443813 - if gn_unittests is run from any dir other
  # than the checkout root, it'll fail.
  api.chromium.runtest('gn_unittests', cwd=api.path['checkout'])

  sha1 = api.file.sha1('compute sha1', path_to_binary, display_result=True)

  api.gsutil.upload(path_to_binary, 'chromium-gn', sha1)


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test

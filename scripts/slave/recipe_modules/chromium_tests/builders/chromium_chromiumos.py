# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec


def _chromium_chromiumos_spec(**kwargs):
  return bot_spec.BotSpec.create(
      build_gs_bucket='chromium-chromiumos-archive', **kwargs)


SPEC = {
    'Linux ChromiumOS Full':
        _chromium_chromiumos_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'chromeos',
            },
            archive_build=True,
            gs_bucket='chromium-browser-snapshots',
            gs_acl='public-read',
            simulation_platform='linux',
        ),
}


def _config(name,
            cros_board=None,
            checkout_qemu_image=False,
            target_arch='intel',
            target_bits=64,
            chromium_apply_config=None,
            gclient_apply_config=None,
            chromium_tests_apply_config=None):
  gclient_apply_config = gclient_apply_config or []
  chromium_tests_apply_config = chromium_tests_apply_config or []
  if 'chromeos' not in gclient_apply_config:
    gclient_apply_config.append('chromeos')
  build_config = 'Release' if '-rel' in name else 'Debug'
  cfg = {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'chromium_tests_apply_config': chromium_tests_apply_config,
      'gclient_config': 'chromium',
      'gclient_apply_config': gclient_apply_config,
      'chromium_config_kwargs': {
          'BUILD_CONFIG': build_config,
          'TARGET_ARCH': target_arch,
          'TARGET_BITS': target_bits,
      },
      'execution_mode': bot_spec.COMPILE_AND_TEST,
      'simulation_platform': 'linux',
  }
  if chromium_apply_config:
    cfg['chromium_apply_config'].extend(chromium_apply_config)
  if cros_board:
    cfg['chromium_config_kwargs']['TARGET_CROS_BOARD'] = cros_board
    cfg['chromium_config_kwargs']['TARGET_PLATFORM'] = 'chromeos'
  if checkout_qemu_image:
    cfg['chromium_apply_config'].append('cros_checkout_qemu_image')
  return name, _chromium_chromiumos_spec(**cfg)


SPEC.update([
    _config(
        'linux-chromeos-rel',
        chromium_tests_apply_config=['use_swarming_command_lines'],
        gclient_apply_config=['use_clang_coverage']),
    _config('linux-chromeos-dbg'),
    _config(
        'chromeos-amd64-generic-asan-rel',
        cros_board='amd64-generic',
        checkout_qemu_image=True),
    _config(
        'chromeos-amd64-generic-cfi-thin-lto-rel',
        cros_board='amd64-generic',
        checkout_qemu_image=True),
    _config('chromeos-amd64-generic-dbg', cros_board='amd64-generic'),
    _config(
        'chromeos-amd64-generic-rel',
        cros_board='amd64-generic',
        checkout_qemu_image=True,
        chromium_tests_apply_config=['use_swarming_command_lines']),
    _config(
        'chromeos-arm-generic-dbg',
        cros_board='arm-generic',
        target_arch='arm',
        target_bits=32),
    _config(
        'chromeos-arm-generic-rel',
        cros_board='arm-generic',
        target_arch='arm',
        target_bits=32,
        chromium_tests_apply_config=['use_swarming_command_lines']),
    _config(
        'chromeos-kevin-rel',
        cros_board='kevin',
        target_arch='arm',
        target_bits=32,
        gclient_apply_config=['arm'],
        # Some tests on this bot depend on being unauthenticated with GS, so
        # don't run the tests inside a luci-auth context to avoid having the
        # BOTO config setup for the task's service account.
        # TODO(crbug.com/1057152): Fix this.
        chromium_apply_config=['mb_no_luci_auth'])
])

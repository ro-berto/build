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
            chromium_apply_config=['mb', 'mb_luci_auth'],
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'chromeos',
            },
            bot_type=bot_spec.BUILDER_TESTER,
            compile_targets=[
                'app_list_unittests',
                'base_unittests',
                'browser_tests',
                'cacheinvalidation_unittests',
                'chromeos_unittests',
                'components_unittests',
                'compositor_unittests',
                'content_browsertests',
                'content_unittests',
                'crypto_unittests',
                'dbus_unittests',
                'device_unittests',
                'gcm_unit_tests',
                'google_apis_unittests',
                'gpu_unittests',
                'interactive_ui_tests',
                'ipc_tests',
                'jingle_unittests',
                'media_unittests',
                'message_center_unittests',
                'nacl_loader_unittests',
                'net_unittests',
                'ppapi_unittests',
                'printing_unittests',
                'remoting_unittests',
                'sandbox_linux_unittests',
                'sql_unittests',
                'ui_base_unittests',
                'unit_tests',
                'url_unittests',
                'views_unittests',
            ],
            archive_build=True,
            gs_bucket='chromium-browser-snapshots',
            gs_acl='public-read',
            testing={
                'platform': 'linux',
            },
        ),
}


def _config(name,
            cros_board=None,
            target_arch='intel',
            target_bits=64,
            gclient_apply_config=None):
  gclient_apply_config = gclient_apply_config or []
  if 'chromeos' not in gclient_apply_config:
    gclient_apply_config.append('chromeos')
  build_config = 'Release' if '-rel' in name else 'Debug'
  cfg = {
      'chromium_config': 'chromium',
      # TODO(crbug.com/1060857): Remove 'mb_luci_auth' when task templates can
      # handle it themselves.
      'chromium_apply_config': ['mb', 'mb_luci_auth'],
      'gclient_config': 'chromium',
      'gclient_apply_config': gclient_apply_config,
      'chromium_config_kwargs': {
          'BUILD_CONFIG': build_config,
          'TARGET_ARCH': target_arch,
          'TARGET_BITS': target_bits,
      },
      'bot_type': bot_spec.BUILDER_TESTER,
      'testing': {
          'platform': 'linux',
      },
      'tests': {},
  }
  if cros_board:
    cfg['chromium_config_kwargs']['TARGET_CROS_BOARD'] = cros_board
    cfg['chromium_config_kwargs']['TARGET_PLATFORM'] = 'chromeos'
  return name, _chromium_chromiumos_spec(**cfg)


SPEC.update([
    _config('linux-chromeos-rel', gclient_apply_config=['use_clang_coverage']),
    _config('linux-chromeos-dbg'),
    _config('chromeos-amd64-generic-asan-rel', cros_board='amd64-generic'),
    _config(
        'chromeos-amd64-generic-cfi-thin-lto-rel', cros_board='amd64-generic'),
    _config('chromeos-amd64-generic-dbg', cros_board='amd64-generic'),
    _config('chromeos-amd64-generic-rel', cros_board='amd64-generic'),
    _config(
        'chromeos-arm-generic-dbg',
        cros_board='arm-generic',
        target_arch='arm',
        target_bits=32),
    _config(
        'chromeos-arm-generic-rel',
        cros_board='arm-generic',
        target_arch='arm',
        target_bits=32),
    _config(
        'chromeos-kevin-rel',
        cros_board='kevin',
        target_arch='arm',
        target_bits=32,
        gclient_apply_config=['arm'])
])

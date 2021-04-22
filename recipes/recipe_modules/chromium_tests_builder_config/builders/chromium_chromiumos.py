# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_chromiumos_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-chromiumos-archive', **kwargs)


SPEC = {
    'Linux ChromiumOS Full':
        _chromium_chromiumos_spec(
            chromium_config='chromium',
            chromium_apply_config=['mb'],
            isolate_server='https://isolateserver.appspot.com',
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
            cros_boards=None,
            cros_boards_with_qemu_images=None,
            target_arch='intel',
            target_bits=64,
            chromium_apply_config=None,
            gclient_apply_config=None,
            **kwargs):
  gclient_apply_config = gclient_apply_config or []
  if 'chromeos' not in gclient_apply_config:
    gclient_apply_config.append('chromeos')
  build_config = 'Release' if '-rel' in name else 'Debug'
  cfg = {
      'chromium_config': 'chromium',
      'chromium_apply_config': ['mb'],
      'gclient_config': 'chromium',
      'gclient_apply_config': gclient_apply_config,
      'isolate_server': 'https://isolateserver.appspot.com',
      'chromium_config_kwargs': {
          'BUILD_CONFIG': build_config,
          'TARGET_ARCH': target_arch,
          'TARGET_BITS': target_bits,
      },
      'execution_mode': builder_spec.COMPILE_AND_TEST,
      'simulation_platform': 'linux',
  }
  cfg.update(**kwargs)
  if chromium_apply_config:
    cfg['chromium_apply_config'].extend(chromium_apply_config)
  if cros_boards:
    cfg['chromium_config_kwargs']['TARGET_CROS_BOARDS'] = cros_boards
    cfg['chromium_config_kwargs']['TARGET_PLATFORM'] = 'chromeos'
  if cros_boards_with_qemu_images:
    cfg['chromium_config_kwargs'][
        'CROS_BOARDS_WITH_QEMU_IMAGES'] = cros_boards_with_qemu_images
    cfg['chromium_config_kwargs']['TARGET_PLATFORM'] = 'chromeos'

  return name, _chromium_chromiumos_spec(**cfg)


SPEC.update([
    _config(
        'lacros-amd64-generic-binary-size-rel',
        cros_boards='amd64-generic',
    ),
    _config(
        'lacros-amd64-generic-rel',
        cros_boards_with_qemu_images='amd64-generic',
    ),
    _config('linux-ash-chromium-generator-rel'),
    _config('linux-chromeos-rel', gclient_apply_config=['use_clang_coverage']),
    _config('linux-chromeos-dbg',),
    _config(
        'linux-chromeos-js-code-coverage',
        gclient_apply_config=['use_clang_coverage']),
    _config('linux-lacros-builder-rel'),
    _config('linux-lacros-rel'),
    _config(
        'linux-lacros-tester-rel',
        execution_mode=builder_spec.TEST,
        parent_buildername='linux-lacros-builder-rel'),
    _config(
        'chromeos-amd64-generic-asan-rel',
        cros_boards_with_qemu_images='amd64-generic'),
    _config(
        'chromeos-amd64-generic-cfi-thin-lto-rel',
        cros_boards_with_qemu_images='amd64-generic'),
    _config(
        'chromeos-amd64-generic-dbg',
        isolate_server='https://isolateserver.appspot.com',
        cros_boards='amd64-generic'),
    _config('chromeos-amd64-generic-lacros-dbg', cros_boards='amd64-generic'),
    _config(
        'chromeos-amd64-generic-rel',
        cros_boards_with_qemu_images='amd64-generic'),
    _config(
        'chromeos-arm-generic-dbg',
        cros_boards='arm-generic',
        target_arch='arm',
        target_bits=32),
    _config(
        'chromeos-arm-generic-rel',
        cros_boards='arm-generic',
        target_arch='arm',
        target_bits=32),
    _config(
        'chromeos-kevin-rel',
        cros_boards='kevin',
        target_arch='arm',
        target_bits=32,
        gclient_apply_config=['arm'],
        # Some tests on this bot depend on being unauthenticated with GS, so
        # don't run the tests inside a luci-auth context to avoid having the
        # BOTO config setup for the task's service account.
        # TODO(crbug.com/1057152): Fix this.
        chromium_apply_config=['mb_no_luci_auth']),
    _config('linux-cfm-rel'),
])

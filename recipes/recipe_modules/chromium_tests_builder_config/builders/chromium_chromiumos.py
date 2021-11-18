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
            gclient_config='chromium',
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'chromeos',
            },
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
      'chromium_config_kwargs': {
          'BUILD_CONFIG': build_config,
          'TARGET_ARCH': target_arch,
          'TARGET_BITS': target_bits,
      },
      'execution_mode': builder_spec.COMPILE_AND_TEST,
      'simulation_platform': 'linux',
  }
  cfg.update(**kwargs)
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
        cros_boards='eve',
        cros_boards_with_qemu_images='amd64-generic',
    ),
    _config(
        'lacros-arm-generic-rel',
        cros_boards='arm-generic',
    ),
    _config('linux-ash-chromium-generator-rel'),
    _config('linux-chromeos-rel', gclient_apply_config=['use_clang_coverage']),
    _config('linux-chromeos-dbg',),
    _config(
        'linux-chromeos-js-code-coverage',
        gclient_apply_config=['use_clang_coverage']),
    _config('linux-chromeos-annotator-rel'),
    _config('linux-lacros-builder-rel'),
    _config('linux-lacros-dbg'),
    _config('linux-lacros-rel'),
    _config('linux-lacros-rel-code-coverage'),
    _config(
        'linux-lacros-tester-rel',
        execution_mode=builder_spec.TEST,
        parent_buildername='linux-lacros-builder-rel'),
    _config('chromeos-amd64-generic-asan-rel', cros_boards='amd64-generic'),
    _config(
        'chromeos-amd64-generic-cfi-thin-lto-rel', cros_boards='amd64-generic'),
    _config('chromeos-amd64-generic-dbg', cros_boards='amd64-generic'),
    _config('chromeos-amd64-generic-lacros-dbg', cros_boards='amd64-generic'),
    _config(
        'chromeos-amd64-generic-rel',
        cros_boards_with_qemu_images='amd64-generic-vm'),
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
        gclient_apply_config=['arm']),
    _config('linux-cfm-rel'),
])

# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def _chromium_chromiumos_spec(**kwargs):
  return builder_spec.BuilderSpec.create(
      build_gs_bucket='chromium-chromiumos-archive', **kwargs)

def _config(name,
            target_arch='intel',
            target_bits=64,
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

  return name, _chromium_chromiumos_spec(**cfg)

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.chromiumos.star
# * Linux ChromiumOS Full
# * chromeos-amd64-generic-asan-rel
# * chromeos-amd64-generic-cfi-thin-lto-rel
# * chromeos-amd64-generic-dbg
# * chromeos-amd64-generic-lacros-dbg
# * chromeos-amd64-generic-rel
# * chromeos-arm-generic-dbg
# * chromeos-arm-generic-rel
# * chromeos-kevin-rel
# * lacros-amd64-generic-binary-size-rel
# * lacros-amd64-generic-rel
# * lacros-arm-generic-rel
# * linux-cfm-rel
# * linux-chromeos-dbg
# * linux-chromeos-rel
# * linux-lacros-builder-rel
# * linux-lacros-dbg
# * linux-lacros-tester-rel

SPEC = dict([
    _config('linux-ash-chromium-generator-rel'),
    _config(
        'linux-chromeos-js-code-coverage',
        gclient_apply_config=['use_clang_coverage']),
    _config('linux-chromeos-annotator-rel'),
    _config('linux-lacros-rel'),
])

# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import builder_spec


def CreateBuilderConfig(platform, config='Release', target_bits=64, **kwargs):
  is_tester = kwargs.get('execution_mode') == builder_spec.TEST
  bot_config = {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb',],
      'chromium_config_kwargs': {
          'BUILD_CONFIG': config,
          'TARGET_BITS': target_bits,
          'TARGET_PLATFORM': platform,
      },
      # The testers are running on linux thin bots regardless the platform.
      'simulation_platform': 'linux' if is_tester else platform,
  }
  bot_config.update(**kwargs)
  return builder_spec.BuilderSpec.create(**bot_config)

# The config for the following builders is now specified src-side in
# //infra/config/subprojects/chromium/ci/chromium.updater.star
# * mac-updater-builder-rel
# * mac-updater-builder-arm64-dbg
# * mac10.13-updater-tester-rel
# * mac10.14-updater-tester-rel
# * mac10.15-updater-tester-rel
# * mac11.0-updater-tester-rel
# * mac-arm64-updater-tester-rel
# * mac-arm64-updater-tester-dbg
# * win-updater-builder-dbg
# * win-updater-builder-rel
# * win10-updater-tester-dbg
# * win10-updater-tester-dbg-uac
# * win10-updater-tester-rel
# * win7-updater-tester-rel

SPEC = {
    # win 32 release builders and testers
    'win32-updater-builder-rel':
        CreateBuilderConfig('win'),
    'win7(32)-updater-tester-rel':
        CreateBuilderConfig(
            'win',
            execution_mode=builder_spec.TEST,
            parent_buildername='win32-updater-builder-rel'),
    # win32 debug builders and testers
    'win32-updater-builder-dbg':
        CreateBuilderConfig('win'),
    # mac debug builders and testers
    'mac-updater-builder-dbg':
        CreateBuilderConfig('mac'),
    'mac10.13-updater-tester-dbg':
        CreateBuilderConfig(
            'mac',
            execution_mode=builder_spec.TEST,
            parent_buildername='mac-updater-builder-dbg'),
    'mac10.14-updater-tester-dbg':
        CreateBuilderConfig(
            'mac',
            execution_mode=builder_spec.TEST,
            parent_buildername='mac-updater-builder-dbg'),
    'mac10.15-updater-tester-dbg':
        CreateBuilderConfig(
            'mac',
            execution_mode=builder_spec.TEST,
            parent_buildername='mac-updater-builder-dbg'),
    'mac11.0-updater-tester-dbg':
        CreateBuilderConfig(
            'mac',
            execution_mode=builder_spec.TEST,
            parent_buildername='mac-updater-builder-dbg'),
}

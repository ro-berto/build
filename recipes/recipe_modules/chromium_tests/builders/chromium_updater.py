# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec


def CreateBuilderConfig(platform, config='Release', target_bits=64, **kwargs):
  bot_config = {
      'chromium_config': 'chromium',
      'gclient_config': 'chromium',
      'chromium_apply_config': ['mb',],
      'chromium_tests_apply_config': [],
      'isolate_server': 'https://isolateserver.appspot.com',
      'chromium_config_kwargs': {
          'BUILD_CONFIG': config,
          'TARGET_BITS': target_bits,
      },
      'chromium_tests_apply_config': [],
      'simulation_platform': platform,
  }
  bot_config.update(**kwargs)
  return bot_spec.BotSpec.create(**bot_config)


SPEC = {
    # release builders and testers
    'win-updater-builder-rel':
        CreateBuilderConfig('win'),
    'win7-updater-tester-rel':
        CreateBuilderConfig(
            'win',
            execution_mode=bot_spec.TEST,
            parent_buildername='win-updater-builder-rel'),
    'win10-updater-tester-rel':
        CreateBuilderConfig(
            'win',
            execution_mode=bot_spec.TEST,
            parent_buildername='win-updater-builder-rel'),
    # win 32 release builders and testers
    'win32-updater-builder-rel':
        CreateBuilderConfig('win'),
    'win7(32)-updater-tester-rel':
        CreateBuilderConfig(
            'win',
            execution_mode=bot_spec.TEST,
            parent_buildername='win32-updater-builder-rel'),
    'mac-updater-builder-rel':
        CreateBuilderConfig('mac'),
    'mac10.11-updater-tester-rel':
        CreateBuilderConfig(
            'mac',
            execution_mode=bot_spec.TEST,
            parent_buildername='mac-updater-builder-rel'),
    'mac10.12-updater-tester-rel':
        CreateBuilderConfig(
            'mac',
            execution_mode=bot_spec.TEST,
            parent_buildername='mac-updater-builder-rel'),
    'mac10.13-updater-tester-rel':
        CreateBuilderConfig(
            'mac',
            execution_mode=bot_spec.TEST,
            parent_buildername='mac-updater-builder-rel'),
    'mac10.14-updater-tester-rel':
        CreateBuilderConfig(
            'mac',
            execution_mode=bot_spec.TEST,
            parent_buildername='mac-updater-builder-rel'),
    'mac10.15-updater-tester-rel':
        CreateBuilderConfig(
            'mac',
            execution_mode=bot_spec.TEST,
            parent_buildername='mac-updater-builder-rel'),
    'mac11.0-updater-tester-rel':
        CreateBuilderConfig(
            'mac',
            execution_mode=bot_spec.TEST,
            parent_buildername='mac-updater-builder-rel'),
    'mac-arm64-updater-tester-rel':
        CreateBuilderConfig(
            'mac',
            execution_mode=bot_spec.TEST,
            parent_buildername='mac-updater-builder-rel'),
    # debug builders and testers
    'win-updater-builder-dbg':
        CreateBuilderConfig('win'),
    'win7-updater-tester-dbg':
        CreateBuilderConfig(
            'win',
            execution_mode=bot_spec.TEST,
            parent_buildername='win-updater-builder-dbg'),
    'win10-updater-tester-dbg':
        CreateBuilderConfig(
            'win',
            execution_mode=bot_spec.TEST,
            parent_buildername='win-updater-builder-dbg'),
    # win32 debug builders and testers
    'win32-updater-builder-dbg':
        CreateBuilderConfig('win'),
    'win7(32)-updater-tester-dbg':
        CreateBuilderConfig(
            'win',
            execution_mode=bot_spec.TEST,
            parent_buildername='win32-updater-builder-dbg'),
    'mac-updater-builder-dbg':
        CreateBuilderConfig('mac'),
    'mac10.15-updater-tester-dbg':
        CreateBuilderConfig(
            'mac',
            execution_mode=bot_spec.TEST,
            parent_buildername='mac-updater-builder-dbg'),
}

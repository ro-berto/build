# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec
from . import chromium_chromiumos


def CreateStandardConfig(platform, apply_configs=None):
  """Generates a builder recipe config for non-Android builder.

    Args:
        platform: win, linux, mac
        apply_configs: list of additional config names to apply.

    Returns:
        A dict mapping string keys to field values in the build config format.
    """

  if apply_configs is None:
    apply_configs = []

  return bot_spec.BotSpec.create(
      chromium_config='chromium',
      # Non-Android builder always uses regular mb.
      chromium_apply_config=(['mb', 'goma_failfast', 'use_autoninja'] +
                             apply_configs),
      isolate_server='https://isolateserver.appspot.com',
      gclient_config='chromium',
      chromium_config_kwargs={
          'TARGET_BITS': 64,
      },
      simulation_platform=platform,
  )


def CreateAndroidConfig(bits, apply_configs=None):
  """Generates a builder recipe config specifically for Android.

    Args:
        bits: Target architecture number of bits (e.g. 32 or 64).
        apply_configs: list of additional config names to apply.

    Returns:
        A dict mapping string keys to field values in the build config format.
    """

  if apply_configs is None:
    apply_configs = []

  return bot_spec.BotSpec.create(
      chromium_config='chromium',
      chromium_apply_config=['goma_failfast', 'use_autoninja'] + apply_configs,
      isolate_server='https://isolateserver.appspot.com',
      gclient_config='chromium',
      gclient_apply_config=['android'],
      chromium_config_kwargs={
          'TARGET_BITS': bits,
          'TARGET_PLATFORM': 'android',
      },
      android_config='main_builder_mb',
      simulation_platform='linux',  # Android builder always uses Linux.
  )


def CreateIosConfig():
  """Generates a builder recipe config for iOS builder.

    Args:
        apply_configs: list of additional config names to apply.

    Returns:
        A dict mapping string keys to field values in the build config format.
    """

  return bot_spec.BotSpec.create(
      chromium_config='chromium',
      chromium_apply_config=([
          'mb', 'mac_toolchain', 'goma_failfast', 'use_autoninja',
          'goma_client_candidate', 'clobber'
      ]),
      isolate_server='https://isolateserver.appspot.com',
      gclient_config='ios',
      chromium_config_kwargs={
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
          'TARGET_PLATFORM': 'ios',
      },
      simulation_platform='mac',
  )


# Predefined builder configs:
_LINUX_CONFIG = CreateStandardConfig('linux')
_LINUX_CLOBBER_CONFIG = CreateStandardConfig('linux', ['clobber'])

_MAC_CONFIG = CreateStandardConfig('mac')
_MAC_CLOBBER_CONFIG = CreateStandardConfig('mac', ['clobber'])

_WIN_CONFIG = CreateStandardConfig('win')
_WIN_CLOBBER_CONFIG = CreateStandardConfig('win', ['clobber'])

_ANDROID32_CONFIG = CreateAndroidConfig(32)

SPEC = {
    # clients5
    'Chromium Linux Goma Staging':
        CreateStandardConfig('linux', ['goma_staging', 'clobber']),
    'Chromium Mac Goma Staging':
        CreateStandardConfig('mac', ['goma_staging', 'clobber']),
    'CrWinGomaStaging':
        CreateStandardConfig('win', ['goma_staging', 'clobber']),

    # Linux RBE
    # TODO(crbug.com/1040754): ToT builders have temporarily been made 'clobber'
    # to test ATS performance.
    'Chromium Linux Goma RBE ToT':
        CreateStandardConfig('linux', ['goma_client_candidate', 'clobber']),
    'Chromium Linux Goma RBE ToT (ATS)':
        CreateStandardConfig('linux', ['goma_client_candidate', 'clobber']),
    'Chromium Linux Goma RBE Staging':
        _LINUX_CONFIG,
    'Chromium Linux Goma RBE Staging (clobber)':
        _LINUX_CLOBBER_CONFIG,
    'Chromium Linux Goma RBE Staging (dbg)':
        _LINUX_CONFIG,
    'Chromium Linux Goma RBE Staging (dbg) (clobber)':
        _LINUX_CLOBBER_CONFIG,
    'chromeos-amd64-generic-rel-goma-rbe-tot':
        chromium_chromiumos.SPEC['chromeos-amd64-generic-rel'].extend(
            chromium_apply_config=['goma_client_candidate']),
    'chromeos-amd64-generic-rel-goma-rbe-staging':
        chromium_chromiumos.SPEC['chromeos-amd64-generic-rel'],

    # Mac RBE
    'Chromium Mac Goma RBE ToT':
        CreateStandardConfig('mac', ['goma_client_candidate']),
    'Chromium Mac Goma RBE Staging':
        _MAC_CONFIG,
    'Chromium Mac Goma RBE Staging (clobber)':
        _MAC_CLOBBER_CONFIG,
    'Chromium Mac Goma RBE Staging (dbg)':
        _MAC_CONFIG,

    # Android ARM 32-bit RBE
    # TODO(crbug.com/1040754): ToT builders have temporarily been made 'clobber'
    # to test ATS performance.
    'Chromium Android ARM 32-bit Goma RBE ToT':
        CreateAndroidConfig(32, ['goma_client_candidate', 'clobber']),
    'Chromium Android ARM 32-bit Goma RBE ToT (ATS)':
        CreateAndroidConfig(32, ['goma_client_candidate', 'clobber']),
    'Chromium Android ARM 32-bit Goma RBE Staging':
        _ANDROID32_CONFIG,

    # Windows RBE
    'Chromium Win Goma RBE ToT':
        CreateStandardConfig('win', ['goma_client_candidate']),
    'Chromium Win Goma RBE Staging':
        _WIN_CONFIG,
    'Chromium Win Goma RBE Staging (clobber)':
        _WIN_CLOBBER_CONFIG,

    # iOS RBE
    'Chromium iOS Goma RBE ToT':
        CreateIosConfig()
}

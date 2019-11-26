# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps


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

  return {
      'chromium_config':
          'chromium',
      # Non-Android builder always uses regular mb.
      'chromium_apply_config': ['mb', 'goma_failfast', 'use_autoninja'] +
                               apply_configs,
      'gclient_config':
          'chromium',
      'chromium_config_kwargs': {
          'TARGET_BITS': 64,
      },
      'testing': {
          'platform': platform,
      },
  }


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

  return {
      'chromium_config':
          'chromium',
      'chromium_apply_config': ['goma_failfast', 'use_autoninja'] +
                               apply_configs,
      'gclient_config':
          'chromium',
      'gclient_apply_config': ['android'],
      'chromium_config_kwargs': {
          'TARGET_BITS': bits,
          'TARGET_PLATFORM': 'android',
      },
      'android_config':
          'main_builder_mb',
      'testing': {
          'platform': 'linux',  # Android builder always uses Linux.
      },
  }


def CreateGenericConfig(chromium_config='chromium',
                        chromium_apply_config=None,
                        gclient_config='chromium',
                        gclient_apply_config=None,
                        chromium_config_kwargs=None,
                        platform='linux'):
  """
    Generates a builder recipe config that differs from the standard config or
    Android config.

    Args:
        chromium_config: base chromium config.
        chromium_apply_configs: list of chromium configs to apply.
        gclient_config: base gclient config.
        gclient_apply_config: list of gclient config to apply.
        chromium_config_kwargs: dict of misc config args.
        platform: one of linux, mac, win

    Returns:
        A dict mapping string keys to field values in the build config format.
    """
  # Specify default values here to avoid mutable object default values in
  # method definition.
  # TODO(crbug.com/947436): |chromium_apply_config| defaults to None but is
  # always specified in current use. If we specify a non-None default value
  # here, the recipes test will complain that it is not covered. Once we need
  # to call this function without explicitly specifying
  # |chromium_apply_config|, then we should provide a proper default value.
  if gclient_apply_config is None:
    gclient_apply_config = []
  if chromium_config_kwargs is None:
    chromium_config_kwargs = {}

  return {
      'chromium_config': chromium_config,
      'chromium_apply_config': chromium_apply_config,
      'gclient_config': gclient_config,
      'gclient_apply_config': gclient_apply_config,
      'chromium_config_kwargs': chromium_config_kwargs,
      'testing': {
          'platform': platform,
      },
  }


# Predefined builder configs:
_LINUX_CONFIG = CreateStandardConfig('linux')
_LINUX_CLOBBER_CONFIG = CreateStandardConfig('linux', ['clobber'])

_MAC_CONFIG = CreateStandardConfig('mac')
_MAC_CLOBBER_CONFIG = CreateStandardConfig('mac', ['clobber'])

_WIN_CONFIG = CreateStandardConfig('win')
_WIN_CLOBBER_CONFIG = CreateStandardConfig('win', ['clobber'])

_ANDROID32_CONFIG = CreateAndroidConfig(32)
_ANDROID32_CLOBBER_CONFIG = CreateAndroidConfig(32, ['clobber'])

_SPEC_BUILDERS = {
    # clients5
    'Chromium Linux Goma Staging':
        CreateStandardConfig('linux', ['goma_staging', 'clobber']),
    'Chromium Mac Goma Staging':
        CreateStandardConfig('mac', ['goma_staging', 'clobber']),
    'CrWinGomaStaging':
        CreateStandardConfig('win', ['goma_staging', 'clobber']),

    # Linux RBE
    'Chromium Linux Goma RBE ToT':
        CreateStandardConfig('linux', ['goma_client_candidate']),
    'Chromium Linux Goma RBE ToT (ATS)':
        CreateStandardConfig('linux', ['goma_client_candidate']),
    'Chromium Linux Goma RBE Staging':
        _LINUX_CONFIG,
    'Chromium Linux Goma RBE Staging (clobber)':
        _LINUX_CLOBBER_CONFIG,
    'Chromium Linux Goma RBE Staging (dbg)':
        _LINUX_CLOBBER_CONFIG,
    'Chromium Linux Goma RBE Staging (dbg) (clobber)':
        _LINUX_CONFIG,
    'Chromium Linux Goma RBE Prod':
        _LINUX_CONFIG,
    'Chromium Linux Goma RBE Prod (clobber)':
        _LINUX_CLOBBER_CONFIG,
    'Chromium Linux Goma RBE Prod (dbg)':
        _LINUX_CONFIG,
    'Chromium Linux Goma RBE Prod (dbg) (clobber)':
        _LINUX_CLOBBER_CONFIG,

    # Mac RBE
    'Chromium Mac Goma RBE ToT':
        CreateStandardConfig('mac', ['goma_client_candidate']),
    'Chromium Mac Goma RBE Staging':
        _MAC_CONFIG,
    'Chromium Mac Goma RBE Staging (clobber)':
        _MAC_CLOBBER_CONFIG,
    'Chromium Mac Goma RBE Staging (dbg)':
        _MAC_CONFIG,
    'Chromium Mac Goma RBE Prod':
        _MAC_CONFIG,
    'Chromium Mac Goma RBE Prod (clobber)':
        _MAC_CLOBBER_CONFIG,
    'Chromium Mac Goma RBE Prod (dbg)':
        _MAC_CONFIG,
    'Chromium Mac Goma RBE Prod (dbg) (clobber)':
        _MAC_CLOBBER_CONFIG,

    # Android ARM 32-bit RBE
    'Chromium Android ARM 32-bit Goma RBE ToT':
        CreateAndroidConfig(32, ['goma_client_candidate']),
    'Chromium Android ARM 32-bit Goma RBE ToT (ATS)':
        CreateAndroidConfig(32, ['goma_client_candidate']),
    'Chromium Android ARM 32-bit Goma RBE Staging':
        _ANDROID32_CONFIG,
    'Chromium Android ARM 32-bit Goma RBE Prod':
        _ANDROID32_CONFIG,
    'Chromium Android ARM 32-bit Goma RBE Prod (clobber)':
        _ANDROID32_CLOBBER_CONFIG,
    'Chromium Android ARM 32-bit Goma RBE Prod (dbg)':
        _ANDROID32_CONFIG,
    'Chromium Android ARM 32-bit Goma RBE Prod (dbg) (clobber)':
        _ANDROID32_CLOBBER_CONFIG,

    # Windows RBE
    'Chromium Win Goma RBE ToT':
        CreateStandardConfig('win', ['goma_client_candidate']),
    'Chromium Win Goma RBE Staging':
        _WIN_CONFIG,
    'Chromium Win Goma RBE Staging (clobber)':
        _WIN_CLOBBER_CONFIG,
    'Chromium Win Goma RBE Prod':
        _WIN_CONFIG,
    'Chromium Win Goma RBE Prod (clobber)':
        _WIN_CLOBBER_CONFIG,
    'Chromium Win Goma RBE Prod (dbg)':
        _WIN_CONFIG,
    'Chromium Win Goma RBE Prod (dbg) (clobber)':
        _WIN_CLOBBER_CONFIG,

    # FYI builders of various config flavors.
    'Cast Linux (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_config='chromium_clang', chromium_apply_config=['mb']),
    'chromeos-amd64-generic-rel (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_apply_config=['mb'],
            gclient_apply_config=['chromeos'],
            chromium_config_kwargs={
                'TARGET_CROS_BOARD': 'amd64-generic',
                'TARGET_PLATFORM': 'chromeos',
            }),
    'Linux ASan LSan Builder (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_config='chromium_asan',
            chromium_apply_config=['lsan', 'mb']),
    'Linux MSan Builder (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_config='chromium_msan', chromium_apply_config=['mb']),
    'fuchsia-fyi-arm64-rel (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_apply_config=['mb'], gclient_apply_config=['fuchsia']),
    'fuchsia-fyi-x64-rel (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_apply_config=['mb'], gclient_apply_config=['fuchsia']),
}


SPEC = {
    'builders': _SPEC_BUILDERS,
}

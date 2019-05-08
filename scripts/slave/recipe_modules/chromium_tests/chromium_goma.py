# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps


def CreateStandardConfig(platform, apply_configs):
    """Generates a builder recipe config for non-Android builder.

    Args:
        platform: win, linux, mac
        apply_configs: list of additional config names to apply.

    Returns:
        A dict mapping string keys to field values in the build config format.
    """

    return {
        'chromium_config': 'chromium',
        # Non-Android builder always uses regular mb.
        'chromium_apply_config': ['mb'] + apply_configs,
        'gclient_config': 'chromium',
        'chromium_config_kwargs': {
            'TARGET_BITS': 64,
        },
        'testing': {
            'platform': platform,
        },
    }


def CreateAndroidConfig(bits, apply_configs):
    """Generates a builder recipe config specifically for Android.

    Args:
        bits: Target architecture number of bits (e.g. 32 or 64).
        apply_configs: list of additional config names to apply.

    Returns:
        A dict mapping string keys to field values in the build config format.
    """

    return {
        'chromium_config': 'chromium',
        'chromium_apply_config': apply_configs,
        'gclient_config': 'chromium',
        'gclient_apply_config': ['android'],
        'chromium_config_kwargs': {
            'TARGET_BITS': bits,
            'TARGET_PLATFORM': 'android',
        },
        'android_config': 'main_builder_mb',
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


SPEC = {
    'builders': {
        # clients5
        'Chromium Linux Goma Staging':
        CreateStandardConfig('linux', ['goma_staging', 'clobber']),
        'Chromium Mac Goma Staging':
        CreateStandardConfig('mac', ['goma_staging', 'clobber']),
        'CrWinGomaStaging':
        CreateStandardConfig('win', ['goma_staging', 'clobber']),

        # Linux RBE
        'Chromium Linux Goma RBE ToT':
        CreateStandardConfig('linux', ['goma_rbe_tot']),
        'Chromium Linux Goma RBE ToT (ATS)':
        CreateStandardConfig('linux', ['goma_rbe_tot']),
        'Chromium Linux Goma RBE Staging':
        CreateStandardConfig('linux', ['goma_mixer_staging']),
        'Chromium Linux Goma RBE Staging (clobber)':
        CreateStandardConfig('linux', ['goma_mixer_staging', 'clobber']),
        'Chromium Linux Goma RBE Staging (dbg)':
        CreateStandardConfig('linux', ['goma_mixer_staging']),
        'Chromium Linux Goma RBE Staging (dbg) (clobber)':
        CreateStandardConfig('linux', ['goma_mixer_staging', 'clobber']),
        'Chromium Linux Goma RBE Prod':
        CreateStandardConfig('linux', ['goma_rbe_prod']),
        'Chromium Linux Goma RBE Prod (clobber)':
        CreateStandardConfig('linux', ['goma_rbe_prod', 'clobber']),
        'Chromium Linux Goma RBE Prod (dbg)':
        CreateStandardConfig('linux', ['goma_rbe_prod']),
        'Chromium Linux Goma RBE Prod (dbg) (clobber)':
        CreateStandardConfig('linux', ['goma_rbe_prod', 'clobber']),

        # Mac RBE
        'Chromium Mac Goma RBE ToT':
        CreateStandardConfig('mac', ['goma_rbe_tot']),
        'Chromium Mac Goma RBE Staging':
        CreateStandardConfig('mac', ['goma_mixer_staging']),
        'Chromium Mac Goma RBE Staging (clobber)':
        CreateStandardConfig('mac', ['goma_mixer_staging', 'clobber']),
        'Chromium Mac Goma RBE Staging (dbg)':
        CreateStandardConfig('mac', ['goma_mixer_staging']),
        'Chromium Mac Goma RBE Prod':
        CreateStandardConfig('mac', ['goma_rbe_prod']),
        'Chromium Mac Goma RBE Prod (clobber)':
        CreateStandardConfig('mac', ['goma_rbe_prod', 'clobber']),
        'Chromium Mac Goma RBE Prod (dbg)':
        CreateStandardConfig('mac', ['goma_rbe_prod']),
        'Chromium Mac Goma RBE Prod (dbg) (clobber)':
        CreateStandardConfig('mac', ['goma_rbe_prod', 'clobber']),

        # Android ARM 32-bit RBE
        'Chromium Android ARM 32-bit Goma RBE ToT':
        CreateAndroidConfig(32, ['goma_rbe_tot']),
        'Chromium Android ARM 32-bit Goma RBE ToT (ATS)':
        CreateAndroidConfig(32, ['goma_rbe_tot']),
        'Chromium Android ARM 32-bit Goma RBE Staging':
        CreateAndroidConfig(32, ['goma_mixer_staging']),
        'Chromium Android ARM 32-bit Goma RBE Prod':
        CreateAndroidConfig(32, ['goma_rbe_prod']),
        'Chromium Android ARM 32-bit Goma RBE Prod (clobber)':
        CreateAndroidConfig(32, ['goma_rbe_prod', 'clobber']),
        'Chromium Android ARM 32-bit Goma RBE Prod (dbg)':
        CreateAndroidConfig(32, ['goma_rbe_prod']),
        'Chromium Android ARM 32-bit Goma RBE Prod (dbg) (clobber)':
        CreateAndroidConfig(32, ['goma_rbe_prod', 'clobber']),

        # Windows RBE
        'Chromium Win Goma RBE ToT':
        CreateStandardConfig('win', ['goma_rbe_tot']),
        'Chromium Win Goma RBE Staging':
        CreateStandardConfig('win', ['goma_mixer_staging']),
        'Chromium Win Goma RBE Staging (clobber)':
        CreateStandardConfig('win', ['goma_mixer_staging', 'clobber']),
        'Chromium Win Goma RBE Prod':
        CreateStandardConfig('win', ['goma_rbe_prod']),
        'Chromium Win Goma RBE Prod (clobber)':
        CreateStandardConfig('win', ['goma_rbe_prod', 'clobber']),
        'Chromium Win Goma RBE Prod (dbg)':
        CreateStandardConfig('win', ['goma_rbe_prod']),
        'Chromium Win Goma RBE Prod (dbg) (clobber)':
        CreateStandardConfig('win', ['goma_rbe_prod', 'clobber']),

        # RBE LoadTest
        'Chromium Linux Goma RBE LoadTest':
        CreateStandardConfig('linux', ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Linux Goma RBE LoadTest (clobber)':
        CreateStandardConfig('linux',
                             ['goma_rbe_prod', 'goma_store_only', 'clobber']),
        'Chromium Linux Goma RBE LoadTest (ATS)':
        CreateStandardConfig('linux', ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Linux Goma RBE LoadTest (ATS) (clobber)':
        CreateStandardConfig('linux',
                             ['goma_rbe_prod', 'goma_store_only', 'clobber']),
        'Chromium Linux Goma RBE LoadTest (debug)':
        CreateStandardConfig('linux', ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Linux Goma RBE LoadTest (clobber) (debug)':
        CreateStandardConfig('linux',
                             ['goma_rbe_prod', 'goma_store_only', 'clobber']),
        'Chromium Linux Goma RBE LoadTest (ATS) (debug)':
        CreateStandardConfig('linux', ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Linux Goma RBE LoadTest (ATS) (clobber) (debug)':
        CreateStandardConfig('linux',
                             ['goma_rbe_prod', 'goma_store_only', 'clobber']),
        'Chromium Android ARM 32-bit Goma RBE LoadTest':
        CreateAndroidConfig(32, ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Android ARM 32-bit Goma RBE LoadTest (clobber)':
        CreateAndroidConfig(32,
                            ['goma_rbe_prod', 'goma_store_only', 'clobber']),
        'Chromium Android ARM 32-bit Goma RBE LoadTest (ATS)':
        CreateAndroidConfig(32, ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Android ARM 32-bit Goma RBE LoadTest (ATS) (clobber)':
        CreateAndroidConfig(32,
                            ['goma_rbe_prod', 'goma_store_only', 'clobber']),
        'Chromium Android ARM 32-bit Goma RBE LoadTest (debug)':
        CreateAndroidConfig(32, ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Android ARM 32-bit Goma RBE LoadTest (clobber) (debug)':
        CreateAndroidConfig(32,
                            ['goma_rbe_prod', 'goma_store_only', 'clobber']),
        'Chromium Android ARM 32-bit Goma RBE LoadTest (ATS) (debug)':
        CreateAndroidConfig(32, ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Android ARM 32-bit Goma RBE LoadTest (ATS) (clobber) (debug)':
        CreateAndroidConfig(32,
                            ['goma_rbe_prod', 'goma_store_only', 'clobber']),

        # RBE HighLoad LoadTest
        'Chromium Linux Goma RBE Cache HighLoad LoadTest (clobber) (debug)':
        CreateStandardConfig('linux',
                             ['goma_rbe_prod', 'goma_store_only', 'clobber']),

        # RBE Cache LoadTest
        'Chromium Linux Goma RBE Cache LoadTest (clobber) (debug)':
        CreateStandardConfig('linux', ['goma_rbe_prod', 'clobber']),

        # FYI builders of various config flavors.
        'Cast Linux (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_config='chromium_clang',
            chromium_apply_config=['mb', 'goma_rbe_tot']),
        'chromeos-amd64-generic-rel (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_apply_config=['mb', 'goma_rbe_tot'],
            gclient_apply_config=['chromeos_amd64_generic'],
            chromium_config_kwargs={
                'TARGET_CROS_BOARD': 'amd64-generic',
                'TARGET_PLATFORM': 'chromeos',
            }),
        'Linux ASan LSan Builder (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_config='chromium_asan',
            chromium_apply_config=['lsan', 'mb', 'goma_rbe_tot']),
        'Linux MSan Builder (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_config='chromium_msan',
            chromium_apply_config=['mb', 'goma_rbe_tot']),
        'fuchsia-fyi-arm64-rel (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_apply_config=['mb', 'goma_rbe_tot'],
            gclient_apply_config=['fuchsia']),
        'fuchsia-fyi-x64-rel (Goma RBE FYI)':
        CreateGenericConfig(
            chromium_apply_config=['mb', 'goma_rbe_tot'],
            gclient_apply_config=['fuchsia']),
    },
}

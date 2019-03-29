# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps


def CreateConfig(platform, apply_configs):
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


SPEC = {
    'builders': {
        # clients5
        'Chromium Linux Goma Staging':
        CreateConfig('linux', ['goma_staging', 'clobber']),
        'Chromium Mac Goma Staging':
        CreateConfig('mac', ['goma_staging', 'clobber']),
        'CrWinGomaStaging':
        CreateConfig('win', ['goma_staging', 'clobber']),

        # Linux RBE
        'Chromium Linux Goma RBE ToT':
        CreateConfig('linux', ['goma_rbe_tot']),
        'Chromium Linux Goma RBE ToT (ATS)':
        CreateConfig('linux', ['goma_rbe_tot']),
        'Chromium Linux Goma RBE Staging':
        CreateConfig('linux', ['goma_mixer_staging']),
        'Chromium Linux Goma RBE Staging (clobber)':
        CreateConfig('linux', ['goma_mixer_staging', 'clobber']),
        'Chromium Linux Goma RBE Staging (dbg)':
        CreateConfig('linux', ['goma_mixer_staging']),
        'Chromium Linux Goma RBE Staging (dbg) (clobber)':
        CreateConfig('linux', ['goma_mixer_staging', 'clobber']),
        'Chromium Linux Goma RBE Prod':
        CreateConfig('linux', ['goma_rbe_prod']),
        'Chromium Linux Goma RBE Prod (clobber)':
        CreateConfig('linux', ['goma_rbe_prod', 'clobber']),
        'Chromium Linux Goma RBE Prod (dbg)':
        CreateConfig('linux', ['goma_rbe_prod']),
        'Chromium Linux Goma RBE Prod (dbg) (clobber)':
        CreateConfig('linux', ['goma_rbe_prod', 'clobber']),

        # Mac RBE
        'Chromium Mac Goma RBE ToT':
        CreateConfig('mac', ['goma_rbe_tot']),
        'Chromium Mac Goma RBE Staging':
        CreateConfig('mac', ['goma_mixer_staging']),
        'Chromium Mac Goma RBE Staging (clobber)':
        CreateConfig('mac', ['goma_mixer_staging', 'clobber']),
        'Chromium Mac Goma RBE Staging (dbg)':
        CreateConfig('mac', ['goma_mixer_staging']),

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
        CreateConfig('win', ['goma_rbe_tot']),
        'Chromium Win Goma RBE Staging':
        CreateConfig('win', ['goma_mixer_staging']),
        'Chromium Win Goma RBE Staging (clobber)':
        CreateConfig('win', ['goma_mixer_staging', 'clobber']),
        'Chromium Win Goma RBE Prod':
        CreateConfig('win', ['goma_rbe_prod']),
        'Chromium Win Goma RBE Prod (clobber)':
        CreateConfig('win', ['goma_rbe_prod', 'clobber']),
        'Chromium Win Goma RBE Prod (dbg)':
        CreateConfig('win', ['goma_rbe_prod']),
        'Chromium Win Goma RBE Prod (dbg) (clobber)':
        CreateConfig('win', ['goma_rbe_prod', 'clobber']),

        # RBE LoadTest
        'Chromium Linux Goma RBE LoadTest':
        CreateConfig('linux', ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Linux Goma RBE LoadTest (clobber)':
        CreateConfig('linux', ['goma_rbe_prod', 'goma_store_only', 'clobber']),
        'Chromium Linux Goma RBE LoadTest (ATS)':
        CreateConfig('linux', ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Linux Goma RBE LoadTest (ATS) (clobber)':
        CreateConfig('linux', ['goma_rbe_prod', 'goma_store_only', 'clobber']),
        'Chromium Linux Goma RBE LoadTest (debug)':
        CreateConfig('linux', ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Linux Goma RBE LoadTest (clobber) (debug)':
        CreateConfig('linux', ['goma_rbe_prod', 'goma_store_only', 'clobber']),
        'Chromium Linux Goma RBE LoadTest (ATS) (debug)':
        CreateConfig('linux', ['goma_rbe_prod', 'goma_store_only']),
        'Chromium Linux Goma RBE LoadTest (ATS) (clobber) (debug)':
        CreateConfig('linux', ['goma_rbe_prod', 'goma_store_only', 'clobber']),
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

        # RBE Cache LoadTest
        'Chromium Linux Goma RBE Cache LoadTest (clobber) (debug)':
        CreateConfig('linux', ['goma_rbe_prod', 'clobber']),
    },
}

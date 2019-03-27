# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps


def CreateConfig(platform, config_type, apply_configs):
    """Generates a builder recipe config for non-Android builder.

    Args:
        platform: win, linux, mac
        config_type: Release or Debug.
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
            'BUILD_CONFIG': config_type,
            'TARGET_BITS': 64,
        },
        'testing': {
            'platform': platform,
        },
    }


def CreateAndroidConfig(config_type, bits, apply_configs):
    """Generates a builder recipe config specifically for Android.

    Args:
        config_type: Release or Debug.
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
            'BUILD_CONFIG': config_type,
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
        CreateConfig('linux', 'Release', ['goma_staging', 'clobber']),
        'Chromium Mac Goma Staging':
        CreateConfig('mac', 'Release', ['goma_staging', 'clobber']),
        'CrWinGomaStaging':
        CreateConfig('win', 'Release', ['goma_staging', 'clobber']),

        # Linux RBE
        'Chromium Linux Goma RBE ToT':
        CreateConfig('linux', 'Release', ['goma_rbe_tot']),
        'Chromium Linux Goma RBE ToT (ATS)':
        CreateConfig('linux', 'Release', ['goma_rbe_tot']),
        'Chromium Linux Goma RBE Staging':
        CreateConfig('linux', 'Release', ['goma_mixer_staging']),
        'Chromium Linux Goma RBE Staging (clobber)':
        CreateConfig('linux', 'Release', ['goma_mixer_staging', 'clobber']),
        'Chromium Linux Goma RBE Staging (dbg)':
        CreateConfig('linux', 'Debug', ['goma_mixer_staging']),
        'Chromium Linux Goma RBE Staging (dbg) (clobber)':
        CreateConfig('linux', 'Debug', ['goma_mixer_staging', 'clobber']),
        'Chromium Linux Goma RBE Prod':
        CreateConfig('linux', 'Release', ['goma_rbe_prod']),
        'Chromium Linux Goma RBE Prod (clobber)':
        CreateConfig('linux', 'Release', ['goma_rbe_prod', 'clobber']),
        'Chromium Linux Goma RBE Prod (dbg)':
        CreateConfig('linux', 'Debug', ['goma_rbe_prod']),
        'Chromium Linux Goma RBE Prod (dbg) (clobber)':
        CreateConfig('linux', 'Debug', ['goma_rbe_prod', 'clobber']),

        # Mac RBE
        'Chromium Mac Goma RBE ToT':
        CreateConfig('mac', 'Release', ['goma_rbe_tot']),
        'Chromium Mac Goma RBE Staging':
        CreateConfig('mac', 'Release', ['goma_mixer_staging']),
        'Chromium Mac Goma RBE Staging (clobber)':
        CreateConfig('mac', 'Release', ['goma_mixer_staging', 'clobber']),
        'Chromium Mac Goma RBE Staging (dbg)':
        CreateConfig('mac', 'Debug', ['goma_mixer_staging']),

        # Android ARM 32-bit RBE
        'Chromium Android ARM 32-bit Goma RBE ToT':
        CreateAndroidConfig('Release', 32, ['goma_rbe_tot']),
        'Chromium Android ARM 32-bit Goma RBE ToT (ATS)':
        CreateAndroidConfig('Release', 32, ['goma_rbe_tot']),
        'Chromium Android ARM 32-bit Goma RBE Staging':
        CreateAndroidConfig('Release', 32, ['goma_mixer_staging']),
        'Chromium Android ARM 32-bit Goma RBE Prod':
        CreateAndroidConfig('Release', 32, ['goma_rbe_prod']),
        'Chromium Android ARM 32-bit Goma RBE Prod (clobber)':
        CreateAndroidConfig('Release', 32, ['goma_rbe_prod', 'clobber']),
        'Chromium Android ARM 32-bit Goma RBE Prod (dbg)':
        CreateAndroidConfig('Debug', 32, ['goma_rbe_prod']),
        'Chromium Android ARM 32-bit Goma RBE Prod (dbg) (clobber)':
        CreateAndroidConfig('Debug', 32, ['goma_rbe_prod', 'clobber']),

        # Windows RBE
        'Chromium Win Goma RBE ToT':
        CreateConfig('win', 'Release', ['goma_rbe_tot']),
        'Chromium Win Goma RBE Staging':
        CreateConfig('win', 'Release', ['goma_mixer_staging']),
        'Chromium Win Goma RBE Staging (clobber)':
        CreateConfig('win', 'Release', ['goma_mixer_staging', 'clobber']),
        'Chromium Win Goma RBE Prod':
        CreateConfig('win', 'Release', ['goma_rbe_prod']),
        'Chromium Win Goma RBE Prod (clobber)':
        CreateConfig('win', 'Release', ['goma_rbe_prod', 'clobber']),
        'Chromium Win Goma RBE Prod (dbg)':
        CreateConfig('win', 'Debug', ['goma_rbe_prod']),
        'Chromium Win Goma RBE Prod (dbg) (clobber)':
        CreateConfig('win', 'Debug', ['goma_rbe_prod', 'clobber']),

        # RBE LoadTest
        'Chromium Linux Goma RBE LoadTest':
        CreateConfig('linux', 'Release', ['goma_rbe_prod']),
        'Chromium Linux Goma RBE LoadTest (clobber)':
        CreateConfig('linux', 'Release', ['goma_rbe_prod', 'clobber']),
        'Chromium Linux Goma RBE LoadTest (ATS)':
        CreateConfig('linux', 'Release', ['goma_rbe_prod']),
        'Chromium Linux Goma RBE LoadTest (ATS) (clobber)':
        CreateConfig('linux', 'Release', ['goma_rbe_prod', 'clobber']),
        'Chromium Linux Goma RBE LoadTest (debug)':
        CreateConfig('linux', 'Debug', ['goma_rbe_prod']),
        'Chromium Linux Goma RBE LoadTest (clobber) (debug)':
        CreateConfig('linux', 'Debug', ['goma_rbe_prod', 'clobber']),
        'Chromium Linux Goma RBE LoadTest (ATS) (debug)':
        CreateConfig('linux', 'Debug', ['goma_rbe_prod']),
        'Chromium Linux Goma RBE LoadTest (ATS) (clobber) (debug)':
        CreateConfig('linux', 'Debug', ['goma_rbe_prod', 'clobber']),
    },
}

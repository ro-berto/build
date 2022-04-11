# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Contains the bulk of the WebRTC builder configurations so they can be reused
# from multiple recipes.

from __future__ import absolute_import

from recipe_engine.engine_types import freeze
from RECIPE_MODULES.build.chromium_tests_builder_config import (builder_db,
                                                                builder_spec)

CHROMIUM_TEST_SERVICE_ACCOUNT = (
    'chromium-tester@chops-service-accounts.iam.gserviceaccount.com')

CHROME_TEST_SERVICE_ACCOUNT = (
    'chrome-tester@chops-service-accounts.iam.gserviceaccount.com')

RECIPE_CONFIGS = freeze({
    'webrtc': {
        'chromium_config': 'webrtc_default',
        'gclient_config': 'webrtc',
        'test_suite': 'webrtc',
    },
    'webrtc_and_baremetal': {
        'chromium_config': 'webrtc_default',
        'gclient_config': 'webrtc',
        'test_suite': 'webrtc_and_baremetal',
    },
    'webrtc_desktop_perf_swarming': {
        'chromium_config': 'webrtc_default',
        'gclient_config': 'webrtc',
        'test_suite': 'desktop_perf_swarming',
    },
    'webrtc_clang': {
        'chromium_config': 'webrtc_clang',
        'gclient_config': 'webrtc',
        'test_suite': 'webrtc',
    },
    'webrtc_and_baremetal_clang': {
        'chromium_config': 'webrtc_clang',
        'gclient_config': 'webrtc',
        'test_suite': 'webrtc_and_baremetal',
    },
    'webrtc_android': {
        'chromium_config': 'android',
        'chromium_android_config': 'webrtc',
        'gclient_config': 'webrtc',
        'gclient_apply_config': ['android'],
        'test_suite': 'android',
    },
    'webrtc_android_perf_swarming': {
        'chromium_config': 'webrtc_default',
        'chromium_android_config': 'webrtc',
        'gclient_config': 'webrtc',
        'gclient_apply_config': ['android'],
        'test_suite': 'android_perf_swarming',
    },
    'webrtc_android_asan': {
        'chromium_config': 'android_asan',
        'chromium_android_config': 'webrtc',
        'gclient_config': 'webrtc',
        'gclient_apply_config': ['android'],
        'test_suite': 'android',
    },
    'webrtc_ios': {
        'chromium_config': 'webrtc_default',
        'gclient_config': 'webrtc_ios',
        'test_suite': 'ios',
    },
    'webrtc_ios_device': {
        'chromium_config': 'webrtc_default',
        'gclient_config': 'webrtc_ios',
        'test_suite': 'ios_device',
    },
    'webrtc_ios_perf': {
        'chromium_config': 'webrtc_default',
        'gclient_config': 'webrtc_ios',
        'test_suite': 'ios_perf',
    },
    'webrtc_more_configs': {
        'chromium_config': 'webrtc_default',
        'gclient_config': 'webrtc',
        'test_suite': 'more_configs',
    },
    'webrtc_android_more_configs': {
        'chromium_config': 'android',
        'gclient_config': 'webrtc',
        'gclient_apply_config': ['android'],
        'test_suite': 'more_configs',
    },
})

BUILDERS = freeze({
    'luci.webrtc.ci': {
        'settings': {
            'builder_group': 'client.webrtc',
            'build_gs_bucket': 'chromium-webrtc',
        },
        'builders': {
            'Win32 Debug (Clang)': {
                'recipe_config': 'webrtc_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'win'
                },
            },
            'Win32 Release (Clang)': {
                'recipe_config': 'webrtc_and_baremetal_clang',
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
            },
            'Win32 Builder (Clang)': {
                'recipe_config': 'webrtc_clang',
                'bot_type': 'builder',
                'testing': {
                    'platform': 'win'
                },
                'triggers': ['luci.webrtc.perf/Perf Win7',],
            },
            'Win64 Debug (Clang)': {
                'recipe_config': 'webrtc_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'win'
                },
            },
            'Win64 Release (Clang)': {
                'recipe_config': 'webrtc_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'win'
                },
            },
            'Win64 ASan': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['asan'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'swarming_dimensions': {
                    'os': 'Windows-10-15063',
                    'cpu': 'x86-64',
                }
            },
            'Mac64 Debug': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'swarming_dimensions': {
                    'os': 'Mac-11',
                    'cpu': 'x86-64',
                    'cores': '12',
                }
            },
            'Mac64 Release': {
                'recipe_config': 'webrtc_and_baremetal',
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
            },
            'Mac64 Builder': {
                'recipe_config': 'webrtc',
                'bot_type': 'builder',
                'testing': {
                    'platform': 'mac'
                },
                'triggers': ['luci.webrtc.perf/Perf Mac 10.11',],
            },
            'Mac Asan': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['asan'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'swarming_dimensions': {
                    'os': 'Mac-11',
                    'cpu': 'x86-64',
                    'cores': '12',
                }
            },
            'MacARM64 M1 Release': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'swarming_dimensions': {
                    'cpu': 'arm64-64-Apple_M1',
                    'pool': 'WebRTC-baremetal',
                },
            },
            'Linux32 Debug': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86',
                }
            },
            'Linux32 Release': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86',
                }
            },
            'Linux32 Debug (ARM)': {
                'recipe_config': 'webrtc',
                'gclient_apply_config': ['arm'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'Linux32 Release (ARM)': {
                'recipe_config': 'webrtc',
                'gclient_apply_config': ['arm'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'Linux64 Debug': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'Linux64 Release': {
                'recipe_config': 'webrtc_and_baremetal',
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
            },
            'Linux64 Builder': {
                'recipe_config':
                    'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type':
                    'builder',
                'testing': {
                    'platform': 'linux'
                },
                'binary_size_files': ['obj/libwebrtc.a'],
                'triggers': [
                    'luci.webrtc.perf/Perf Linux Trusty',
                    'luci.webrtc.perf/Perf Linux Bionic',
                ],
            },
            'Linux64 Debug (ARM)': {
                'recipe_config': 'webrtc',
                'gclient_apply_config': ['arm64'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'Linux64 Release (ARM)': {
                'recipe_config': 'webrtc',
                'gclient_apply_config': ['arm64'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'Linux Asan': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['asan', 'lsan'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'Linux MSan': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['msan'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-14.04',
                    'cpu': 'x86-64',
                }
            },
            'Linux Tsan v2': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['tsan2'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'Linux UBSan': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['ubsan'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'Linux UBSan vptr': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['ubsan_vptr'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'Android32 Builder x86': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'Android32 Builder x86 (dbg)': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'Android64 Builder x64 (dbg)': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'Android32 (M Nexus5X)(dbg)': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'archive_apprtc': True,
                'swarming_dimensions': {
                    'device_os': 'MMB29Q',  # 6.0.1
                    'device_type': 'bullhead',  # Nexus 5X
                    'os': 'Android',
                    'android_devices': '1',
                }
            },
            'Android32 (M Nexus5X)': {
                'recipe_config': 'webrtc_android',
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'archive_apprtc': True,
                'build_android_archive': True,
            },
            'Android32 Builder arm': {
                'recipe_config':
                    'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type':
                    'builder',
                'testing': {
                    'platform': 'linux'
                },
                'binary_size_files': [
                    'libjingle_peerconnection_so.so', 'apks/AppRTCMobile.apk'
                ],
                'triggers': [
                    'luci.webrtc.perf/Perf Android32 (M Nexus5)',
                    'luci.webrtc.perf/Perf Android32 (M AOSP Nexus6)',
                ],
            },
            'Android64 (M Nexus5X)(dbg)': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'archive_apprtc': True,
                'swarming_dimensions': {
                    'device_type': 'bullhead',  # Nexus 5X
                    'device_os': 'MMB29Q',  # 6.0.1
                    'os': 'Android',
                    'android_devices': '1',
                }
            },
            'Android64 (M Nexus5X)': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'archive_apprtc': True,
                'swarming_dimensions': {
                    'device_type': 'bullhead',  # Nexus 5X
                    'device_os': 'MMB29Q',  # 6.0.1
                    'os': 'Android',
                    'android_devices': '1',
                }
            },
            'Android64 Builder arm64': {
                'recipe_config':
                    'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type':
                    'builder',
                'testing': {
                    'platform': 'linux'
                },
                'binary_size_files': [
                    'libjingle_peerconnection_so.so', 'apks/AppRTCMobile.apk'
                ],
                'triggers': [
                    'luci.webrtc.perf/Perf Android64 (M Nexus5X)',
                    'luci.webrtc.perf/Perf Android64 (O Pixel2)',
                ],
            },
            'iOS64 Debug': {
                'recipe_config': 'webrtc_ios',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'mac'
                },
            },
            'iOS64 Release': {
                'recipe_config': 'webrtc_ios',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'mac'
                },
            },
            'iOS64 Sim Debug (iOS 14.0)': {
                'recipe_config': 'webrtc_ios',
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
            },
            'iOS64 Sim Debug (iOS 13)': {
                'recipe_config': 'webrtc_ios',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'service_account': CHROMIUM_TEST_SERVICE_ACCOUNT,
                'platform': 'iPhone X',
                'version': '13.6',
                'swarming_dimensions': {
                    'os': 'Mac-11',
                },
            },
            'iOS64 Sim Debug (iOS 12)': {
                'recipe_config': 'webrtc_ios',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'service_account': CHROMIUM_TEST_SERVICE_ACCOUNT,
                'platform': 'iPhone X',
                'version': '12.4',
                'swarming_dimensions': {
                    'os': 'Mac-11',
                },
            },
            'Linux (more configs)': {
                'recipe_config': 'webrtc_more_configs',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'phases': [
                    'bwe_test_logging', 'dummy_audio_file_devices_no_protobuf',
                    'rtti_no_sctp'
                ],
                'swarming_dimensions': {
                    'os': 'Ubuntu-16.04',
                    'cpu': 'x86-64',
                },
            },
            'Android32 (more configs)': {
                'recipe_config':
                    'webrtc_android_more_configs',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type':
                    'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'phases': [
                    'bwe_test_logging', 'dummy_audio_file_devices_no_protobuf',
                    'rtti_no_sctp'
                ],
            },
            'Win (more configs)': {
                'recipe_config': 'webrtc_more_configs',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'phases': [
                    'bwe_test_logging', 'dummy_audio_file_devices_no_protobuf',
                    'rtti_no_sctp'
                ],
                'swarming_dimensions': {
                    'os': 'Windows-7-SP1',
                    'cpu': 'x86-64',
                },
            },
        },
    },
    'luci.webrtc.perf': {
        'settings': {
            'builder_group': 'client.webrtc.perf',
            'build_gs_bucket': 'chromium-webrtc',
        },
        'builders': {
            'Perf Win7': {
                'recipe_config': 'webrtc_desktop_perf_swarming',
                'perf_id': 'webrtc-win-large-tests',
                'bot_type': 'tester',
                'parent_buildername': 'Win32 Builder (Clang)',
                'testing': {
                    'platform': 'win'
                },
            },
            'Perf Mac 10.11': {
                'recipe_config': 'webrtc_desktop_perf_swarming',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'perf_id': 'webrtc-mac-large-tests',
                'bot_type': 'tester',
                'parent_buildername': 'Mac64 Builder',
                'testing': {
                    'platform': 'mac'
                },
                'swarming_dimensions': {
                    'pool': 'WebRTC-perf',
                    'gpu': None,
                    'os': 'Mac-10.12',
                },
                'swarming_timeout': 10800,  # 3h
            },
            # TODO(tikuta): remove this (crbug.com/954875)
            'Perf Linux Trusty': {
                'recipe_config': 'webrtc_desktop_perf_swarming',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'perf_id': 'webrtc-linux-large-tests',
                'bot_type': 'tester',
                'parent_buildername': 'Linux64 Builder',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'pool': 'WebRTC-perf',
                    'gpu': None,
                    'os': 'Ubuntu-14.04',
                },
                'swarming_timeout': 10800,  # 3h
            },
            'Perf Linux Bionic': {
                'recipe_config': 'webrtc_desktop_perf_swarming',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'perf_id': 'webrtc-linux-tests-bionic',
                'bot_type': 'tester',
                'parent_buildername': 'Linux64 Builder',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'pool': 'WebRTC-perf',
                    'gpu': None,
                    'os': 'Ubuntu-18.04',
                },
                'swarming_timeout': 10800,  # 3h
            },
            'Perf Android32 (M Nexus5)': {
                'recipe_config': 'webrtc_android_perf_swarming',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'perf_id': 'webrtc-android-tests-nexus5-marshmallow',
                'bot_type': 'tester',
                'parent_buildername': 'Android32 Builder arm',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'pool': 'WebRTC-perf',
                    'os': 'Android',
                    'android_devices': '1',
                    'device_type': 'hammerhead',  # Nexus 5.
                    'device_os': 'M',
                },
                'swarming_timeout': 10800,  # 3h
            },
            'Perf Android32 (M AOSP Nexus6)': {
                'recipe_config': 'webrtc_android_perf_swarming',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'perf_id': 'webrtc-android-tests-nexus6-mob30k',
                'bot_type': 'tester',
                'parent_buildername': 'Android32 Builder arm',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'pool': 'WebRTC-perf',
                    'os': 'Android',
                    'android_devices': '1',
                    'device_type': 'shamu',  # Nexus 6.
                    'device_os': 'MOB30K',
                },
                'swarming_timeout': 10800,  # 3h
            },
            'Perf Android64 (M Nexus5X)': {
                'recipe_config': 'webrtc_android_perf_swarming',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'perf_id': 'webrtc-android-tests-nexus5x-marshmallow',
                'bot_type': 'tester',
                'parent_buildername': 'Android64 Builder arm64',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'pool': 'WebRTC-perf',
                    'os': 'Android',
                    'android_devices': '1',
                    'device_type': 'bullhead',  # Nexus 5X.
                    'device_os': 'MMB29Q',
                },
                'swarming_timeout': 10800,  # 3h
            },
            'Perf Android64 (O Pixel2)': {
                'recipe_config': 'webrtc_android_perf_swarming',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'perf_id': 'webrtc-android-tests-pixel2-oreo',
                'bot_type': 'tester',
                'parent_buildername': 'Android64 Builder arm64',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'pool': 'WebRTC-perf',
                    'os': 'Android',
                    'android_devices': '1',
                    'device_type': 'walleye',  # Pixel 2.
                    'device_os': 'O',
                },
                'swarming_timeout': 10800,  # 3h
            },
        },
    },
    'luci.webrtc.try': {
        'settings': {
            'builder_group': 'tryserver.webrtc',
            'build_gs_bucket': 'chromium-webrtc',
        },
        'builders': {
            'win_compile_x86_clang_dbg': {
                'recipe_config': 'webrtc_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'win'
                },
            },
            'win_compile_x86_clang_rel': {
                'recipe_config': 'webrtc_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'win'
                },
            },
            'win_compile_x64_clang_dbg': {
                'recipe_config': 'webrtc_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'win'
                },
            },
            'win_compile_x64_clang_rel': {
                'recipe_config': 'webrtc_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'win'
                },
            },
            'win_x86_clang_dbg': {
                'recipe_config': 'webrtc_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'swarming_dimensions': {
                    'os': 'Windows-7-SP1',
                    'cpu': 'x86-64',
                },
            },
            'win_x86_clang_rel': {
                'recipe_config': 'webrtc_and_baremetal_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'swarming_dimensions': {
                    'os': 'Windows-7-SP1',
                    'cpu': 'x86-64',
                },
                'baremetal_swarming_dimensions': {
                    'pool': 'WebRTC-baremetal-try',
                    'os': 'Windows',
                    'cpu': 'x86',
                    'gpu': None,
                }
            },
            'win_x64_clang_dbg': {
                'recipe_config': 'webrtc_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'swarming_dimensions': {
                    'os': 'Windows-7-SP1',
                    'cpu': 'x86-64',
                },
            },
            'win_x64_clang_rel': {
                'recipe_config': 'webrtc_clang',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'swarming_dimensions': {
                    'os': 'Windows-7-SP1',
                    'cpu': 'x86-64',
                },
            },
            'win_asan': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['asan'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'swarming_dimensions': {
                    'os': 'Windows-10-15063',
                    'cpu': 'x86-64',
                }
            },
            'win_x64_clang_dbg_win10': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'swarming_dimensions': {
                    'os': 'Windows-10-15063',
                    'cpu': 'x86-64',
                }
            },
            'mac_compile_dbg': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'mac'
                },
            },
            'mac_compile_rel': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'mac'
                },
            },
            'mac_dbg': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'swarming_dimensions': {
                    'os': 'Mac-11',
                    'cpu': 'x86-64',
                    'cores': '12',
                }
            },
            'mac_rel': {
                'recipe_config': 'webrtc_and_baremetal',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'swarming_dimensions': {
                    'os': 'Mac-11',
                    'cpu': 'x86-64',
                },
                'baremetal_swarming_dimensions': {
                    'pool': 'WebRTC-baremetal-try',
                    'os': 'Mac',
                    'gpu': None,
                }
            },
            'mac_asan': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['asan'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'swarming_dimensions': {
                    'os': 'Mac-11',
                    'cpu': 'x86-64',
                    'cores': '12',
                }
            },
            'mac_rel_m1': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                    'TARGET_ARCH': 'arm'
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'swarming_dimensions': {
                    'cpu': 'arm64-64-Apple_M1',
                    'pool': 'WebRTC-baremetal-try',
                },
            },
            'mac_dbg_m1': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                    'TARGET_ARCH': 'arm'
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'swarming_dimensions': {
                    'cpu': 'arm64-64-Apple_M1',
                    'pool': 'WebRTC-baremetal-try',
                },
            },
            'linux_compile_dbg': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'linux_compile_rel': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
                'binary_size_files': ['obj/libwebrtc.a'],
            },
            'linux_dbg': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'linux_rel': {
                'recipe_config': 'webrtc_and_baremetal',
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
            },
            'linux_compile_arm64_dbg': {
                'recipe_config': 'webrtc',
                'gclient_apply_config': ['arm64'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'linux_compile_arm64_rel': {
                'recipe_config': 'webrtc',
                'gclient_apply_config': ['arm64'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'linux_x86_dbg': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86',
                }
            },
            'linux_x86_rel': {
                'recipe_config': 'webrtc',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86',
                }
            },
            'linux_compile_arm_dbg': {
                'recipe_config': 'webrtc',
                'gclient_apply_config': ['arm'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'linux_compile_arm_rel': {
                'recipe_config': 'webrtc',
                'gclient_apply_config': ['arm'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'linux_asan': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['asan', 'lsan'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'linux_memcheck': {
                'recipe_config': 'webrtc',
                'chromium_apply_config': ['memcheck'],
                'gclient_apply_config': ['webrtc_valgrind'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'linux_msan': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['msan'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-14.04',
                    'cpu': 'x86-64',
                }
            },
            'linux_tsan2': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['tsan2'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'linux_ubsan': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['ubsan'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'linux_ubsan_vptr': {
                'recipe_config': 'webrtc_clang',
                'chromium_apply_config': ['ubsan_vptr'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'os': 'Ubuntu-18.04',
                    'cpu': 'x86-64',
                }
            },
            'android_compile_arm_dbg': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'android_compile_arm_rel': {
                'recipe_config':
                    'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type':
                    'builder',
                'testing': {
                    'platform': 'linux'
                },
                'binary_size_files': [
                    'libjingle_peerconnection_so.so', 'apks/AppRTCMobile.apk'
                ],
            },
            'android_compile_arm64_dbg': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'android_compile_arm64_rel': {
                'recipe_config':
                    'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type':
                    'builder',
                'testing': {
                    'platform': 'linux'
                },
                'binary_size_files': [
                    'libjingle_peerconnection_so.so', 'apks/AppRTCMobile.apk'
                ],
            },
            'android_compile_x86_dbg': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'android_compile_x86_rel': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'android_compile_x64_dbg': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'android_compile_x64_rel': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'linux'
                },
            },
            'android_arm_dbg': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'device_type': 'bullhead',  # Nexus 5X
                    'device_os': 'MMB29Q',  # 6.0.1
                    'os': 'Android',
                    'android_devices': '1',
                }
            },
            'android_arm_rel': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'build_android_archive': True,
                'swarming_dimensions': {
                    'device_type': 'bullhead',  # Nexus 5X
                    'device_os': 'MMB29Q',  # 6.0.1
                    'os': 'Android',
                    'android_devices': '1',
                }
            },
            'android_arm64_dbg': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'device_type': 'bullhead',  # Nexus 5X
                    'device_os': 'MMB29Q',  # 6.0.1
                    'os': 'Android',
                    'android_devices': '1',
                }
            },
            'android_arm64_rel': {
                'recipe_config': 'webrtc_android',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'swarming_dimensions': {
                    'device_type': 'bullhead',  # Nexus 5X
                    'device_os': 'MMB29Q',  # 6.0.1
                    'os': 'Android',
                    'android_devices': '1',
                }
            },
            'ios_compile_arm64_dbg': {
                'recipe_config': 'webrtc_ios',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'mac'
                },
            },
            'ios_compile_arm64_rel': {
                'recipe_config': 'webrtc_ios',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder',
                'testing': {
                    'platform': 'mac'
                },
            },
            'ios_sim_x64_dbg_ios14': {
                'recipe_config': 'webrtc_ios',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'service_account': CHROMIUM_TEST_SERVICE_ACCOUNT,
                'platform': 'iPhone X',
                'version': '14.0',
                'swarming_dimensions': {
                    'os': 'Mac-11',
                },
            },
            'ios_sim_x64_dbg_ios13': {
                'recipe_config': 'webrtc_ios',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'service_account': CHROMIUM_TEST_SERVICE_ACCOUNT,
                'platform': 'iPhone X',
                'version': '13.6',
                'swarming_dimensions': {
                    'os': 'Mac-11',
                },
            },
            'ios_sim_x64_dbg_ios12': {
                'recipe_config': 'webrtc_ios',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'intel',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'service_account': CHROMIUM_TEST_SERVICE_ACCOUNT,
                'platform': 'iPhone X',
                'version': '12.4',
                'swarming_dimensions': {
                    'os': 'Mac-11',
                },
            },
            'linux_more_configs': {
                'recipe_config': 'webrtc_more_configs',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'phases': [
                    'bwe_test_logging', 'dummy_audio_file_devices_no_protobuf',
                    'rtti_no_sctp'
                ],
                'swarming_dimensions': {
                    'os': 'Ubuntu-16.04',
                    'cpu': 'x86-64',
                },
            },
            'android_arm_more_configs': {
                'recipe_config':
                    'webrtc_android_more_configs',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'android',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 32,
                },
                'bot_type':
                    'builder_tester',
                'testing': {
                    'platform': 'linux'
                },
                'phases': [
                    'bwe_test_logging', 'dummy_audio_file_devices_no_protobuf',
                    'rtti_no_sctp'
                ],
            },
            'win_x86_more_configs': {
                'recipe_config': 'webrtc_more_configs',
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'win'
                },
                'phases': [
                    'bwe_test_logging', 'dummy_audio_file_devices_no_protobuf',
                    'rtti_no_sctp'
                ],
                'swarming_dimensions': {
                    'os': 'Windows-7-SP1',
                    'cpu': 'x86-64',
                },
            },
        },
    },
    'luci.webrtc-internal.ci': {
        'settings': {
            'builder_group': 'internal.client.webrtc',
        },
        'builders': {
            'iOS64 Debug': {
                'recipe_config': 'webrtc_ios_device',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'service_account': CHROME_TEST_SERVICE_ACCOUNT,
                'swarming_dimensions': {
                    'os': 'iOS-15.3',
                    'pool': 'chrome.tests',
                },
            },
            'iOS64 Release': {
                'recipe_config': 'webrtc_ios_device',
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
            },
            'iOS64 Perf': {
                'recipe_config': 'webrtc_ios_perf',
                'bot_type': 'builder_tester',
                'perf_id': 'webrtc-ios-tests',
                'testing': {
                    'platform': 'mac'
                },
            },
        },
    },
    'luci.webrtc-internal.try': {
        'settings': {
            'builder_group': 'internal.tryserver.webrtc',
        },
        'builders': {
            'ios_arm64_dbg': {
                'recipe_config': 'webrtc_ios_device',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Debug',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'service_account': CHROME_TEST_SERVICE_ACCOUNT,
                'swarming_dimensions': {
                    'os': 'iOS-15.3',
                    'pool': 'chrome.tests',
                },
            },
            'ios_arm64_rel': {
                'recipe_config': 'webrtc_ios_device',
                'chromium_apply_config': ['mac_toolchain'],
                'chromium_config_kwargs': {
                    'BUILD_CONFIG': 'Release',
                    'TARGET_PLATFORM': 'ios',
                    'TARGET_ARCH': 'arm',
                    'TARGET_BITS': 64,
                },
                'bot_type': 'builder_tester',
                'testing': {
                    'platform': 'mac'
                },
                'service_account': CHROME_TEST_SERVICE_ACCOUNT,
                'swarming_dimensions': {
                    'os': 'iOS-15.3',
                    'pool': 'chrome.tests',
                },
            },
        },
    },
})

_CLIENT_WEBRTC_SPEC = {
    'Android32 (M Nexus5X)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'Android32 (M Nexus5X)(dbg)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'Android32 (more configs)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'Android32 Builder arm':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'Android32 Builder x86':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 32,
            }),
    'Android32 Builder x86 (dbg)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 32,
            }),
    'Android64 (M Nexus5X)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'Android64 (M Nexus5X)(dbg)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'Android64 Builder arm64':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'Android64 Builder x64 (dbg)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            }),
    'Linux (more configs)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'Linux Asan':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['asan', 'lsan'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Linux MSan':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['msan'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Linux Tsan v2':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['tsan2'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Linux UBSan':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['ubsan'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Linux UBSan vptr':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['ubsan_vptr'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Linux32 Debug':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            }),
    'Linux32 Debug (ARM)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            gclient_apply_config=['arm'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'Linux32 Release':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            }),
    'Linux32 Release (ARM)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            gclient_apply_config=['arm'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'Linux64 Debug':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'Linux64 Debug (ARM)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            gclient_apply_config=['arm64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'Linux64 Builder':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Linux64 Release':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Linux64 Release (ARM)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            gclient_apply_config=['arm64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'Linux64 Release (Libfuzzer)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Mac Asan':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['asan'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Mac64 Builder':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Mac64 Debug':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'Mac64 Release':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'MacARM64 M1 Release':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Win (more configs)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'Win32 Builder (Clang)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            }),
    'Win32 Debug (Clang)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            }),
    'Win32 Release (Clang)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            }),
    'Win64 ASan':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['asan'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Win64 Debug (Clang)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'Win64 Release (Clang)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'iOS64 Debug':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'iOS64 Release':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'iOS64 Sim Debug (iOS 12)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            }),
    'iOS64 Sim Debug (iOS 13)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            }),
    'iOS64 Sim Debug (iOS 14.0)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            }),
}

_CLIENT_WEBRTC_PERF_SPECS = {
    'Perf Android32 (M AOSP Nexus6)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            execution_mode=builder_spec.TEST,
            parent_builder_group='client.webrtc',
            parent_buildername='Android32 Builder arm',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'Perf Android32 (M Nexus5)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            execution_mode=builder_spec.TEST,
            parent_builder_group='client.webrtc',
            parent_buildername='Android32 Builder arm',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'Perf Android64 (M Nexus5X)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            execution_mode=builder_spec.TEST,
            parent_builder_group='client.webrtc',
            parent_buildername='Android64 Builder arm64',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'Perf Android64 (O Pixel2)':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            execution_mode=builder_spec.TEST,
            parent_builder_group='client.webrtc',
            parent_buildername='Android64 Builder arm64',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'Perf Linux Bionic':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            execution_mode=builder_spec.TEST,
            parent_builder_group='client.webrtc',
            parent_buildername='Linux64 Builder',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Perf Linux Trusty':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            execution_mode=builder_spec.TEST,
            parent_builder_group='client.webrtc',
            parent_buildername='Linux64 Builder',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Perf Mac 10.11':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            execution_mode=builder_spec.TEST,
            parent_builder_group='client.webrtc',
            parent_buildername='Mac64 Builder',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'Perf Win7':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            execution_mode=builder_spec.TEST,
            parent_builder_group='client.webrtc',
            parent_buildername='Win32 Builder (Clang)',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            }),
}

_INTERNAL_CLIENT_WEBRTC_SPECS = {
    'iOS64 Debug':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'iOS64 Perf':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'iOS64 Release':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
}

_INTERNAL_TRYSERVER_WEBRTC_SPECS = {
    'ios_arm64_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'ios_arm64_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
}

_TRYSERVER_WEBRTC_SPEC = {
    'android_compile_arm_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'android_compile_arm_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'android_compile_arm64_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'android_compile_arm64_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'android_compile_x86_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 32,
            }),
    'android_compile_x86_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 32,
            }),
    'android_compile_x64_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            }),
    'android_compile_x64_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            }),
    'android_arm_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'android_arm_more_configs':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'android_arm_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'android_arm64_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'android_arm64_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_android',
            android_config='webrtc',
            gclient_config='webrtc',
            gclient_apply_config=['android'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'android',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'ios_compile_arm64_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'ios_compile_arm64_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'ios_sim_x64_dbg_ios14':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            }),
    'ios_sim_x64_dbg_ios13':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            }),
    'ios_sim_x64_dbg_ios12':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc_ios',
            chromium_apply_config=['mac_toolchain'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_PLATFORM': 'ios',
                'TARGET_ARCH': 'intel',
                'TARGET_BITS': 64,
            }),
    'linux_asan':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['asan', 'lsan'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'linux_compile_arm_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            gclient_apply_config=['arm'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'linux_compile_arm_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            gclient_apply_config=['arm'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 32,
            }),
    'linux_compile_arm64_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            gclient_apply_config=['arm64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'linux_compile_arm64_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            gclient_apply_config=['arm64'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
            }),
    'linux_compile_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'linux_compile_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'linux_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'linux_libfuzzer_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'linux_memcheck':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_apply_config=['memcheck'],
            gclient_apply_config=['webrtc_valgrind'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'linux_more_configs':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'linux_msan':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['msan'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'linux_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'linux_tsan2':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['tsan2'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'linux_ubsan':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['ubsan'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'linux_ubsan_vptr':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['ubsan_vptr'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'linux_x86_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            }),
    'linux_x86_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            }),
    'mac_asan':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['asan'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'mac_compile_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'mac_compile_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'mac_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'mac_dbg_m1':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
                'TARGET_ARCH': 'arm'
            }),
    'mac_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'mac_rel_m1':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
                'TARGET_ARCH': 'arm'
            }),
    'win_asan':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_apply_config=['asan'],
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'win_compile_x64_clang_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'win_compile_x64_clang_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'win_compile_x86_clang_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            }),
    'win_compile_x86_clang_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            }),
    'win_x64_clang_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'win_x64_clang_dbg_win10':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
    'win_x64_clang_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64,
            }),
    'win_x86_clang_dbg':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 32,
            }),
    'win_x86_clang_rel':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_clang',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32,
            }),
    'win_x86_more_configs':
        builder_spec.BuilderSpec.create(
            chromium_config='webrtc_default',
            gclient_config='webrtc',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Debug',
                'TARGET_BITS': 64,
            }),
}

BUILDERS_DB = builder_db.BuilderDatabase.create({
    'client.webrtc': _CLIENT_WEBRTC_SPEC,
    'client.webrtc.perf': _CLIENT_WEBRTC_PERF_SPECS,
    'internal.client.webrtc': _INTERNAL_CLIENT_WEBRTC_SPECS,
    'internal.tryserver.webrtc': _INTERNAL_TRYSERVER_WEBRTC_SPECS,
    'tryserver.webrtc': _TRYSERVER_WEBRTC_SPEC,
})

# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Contains the bulk of the WebRTC builder configurations so they can be reused
# from multiple recipes.

from recipe_engine.types import freeze

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
})

BUILDERS = freeze({
  'luci.webrtc.ci': {
    'settings': {
      'mastername': 'client.webrtc',
      'build_gs_bucket': 'chromium-webrtc',
    },
    'builders': {
      'Win32 Debug': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        }
      },
      'Win32 Release': {
        'recipe_config': 'webrtc_and_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        },
        'baremetal_swarming_dimensions': {
          'pool': 'WebRTC-baremetal',
          'os': 'Windows',
          'gpu': None,
        }
      },
      'Win64 Debug': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        }
      },
      'Win64 Release': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        }
      },
      'Win32 Debug (Clang)': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'Win32 Release (Clang)': {
        'recipe_config': 'webrtc_and_baremetal_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        },
        'baremetal_swarming_dimensions': {
          'pool': 'WebRTC-baremetal',
          'os': 'Windows',
          'gpu': None,
        }
      },
      'Win32 Builder (Clang)': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
        'triggers': [
          'luci.webrtc.perf/Perf Win7',
        ],
      },
      'Win64 Debug (Clang)': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'Win64 Release (Clang)': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'Win64 ASan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-10',
          'cpu': 'x86-64',
        }
      },
      'Win64 UWP': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'Mac64 Debug': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        }
      },
      'Mac64 Release': {
        'recipe_config': 'webrtc_and_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        },
        'baremetal_swarming_dimensions': {
          'pool': 'WebRTC-baremetal',
          'os': 'Mac',
          'gpu': None,
        }
      },
      'Mac64 Builder': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
        'triggers': [
          'luci.webrtc.perf/Perf Mac 10.11',
        ],
      },
      'Mac Asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        }
      },
      'Linux32 Debug': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
      },
      'Linux64 Debug': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
          'cpu': 'x86-64',
        }
      },
      'Linux64 Release': {
        'recipe_config': 'webrtc_and_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
          'cpu': 'x86-64',
        },
        'baremetal_swarming_dimensions': {
          'pool': 'WebRTC-baremetal',
          'os': 'Ubuntu',
          'gpu': None,
        }
      },
      'Linux64 Builder': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'binary_size_files': [
          'obj/libwebrtc.a'
        ],
        'triggers': [
          'luci.webrtc.perf/Perf Linux Trusty',
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
      },
      'Linux64 Release (GCC)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },

      'Linux Asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan', 'lsan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
        'archive_apprtc': True,
        'swarming_dimensions': {
          'device_os': 'MMB29Q', # 6.0.1
          'device_type': 'bullhead', # Nexus 5X
          'os': 'Android',
          'android_devices': '1',
        }
      },
      'Android32 (M Nexus5X)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'archive_apprtc': True,
        'build_android_archive': True,
        # TODO(bugs.webrtc.org/8642): Re-enable when it is fixed and stable.
        # 'test_android_studio_project_generation': True,
        'swarming_dimensions': {
          'device_os': 'MMB29Q', # 6.0.1
          'device_type': 'bullhead', # Nexus 5X
          'os': 'Android',
          'android_devices': '1',
        }
      },
      'Android32 Builder arm': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'binary_size_files': [
          'libjingle_peerconnection_so.so',
          'apks/AppRTCMobile.apk'
        ],
        'triggers': [
          'luci.webrtc.perf/Perf Android32 (K Nexus5)',
          'luci.webrtc.perf/Perf Android32 (L Nexus4)',
          'luci.webrtc.perf/Perf Android32 (L Nexus5)',
          'luci.webrtc.perf/Perf Android32 (L Nexus6)',
          'luci.webrtc.perf/Perf Android32 (L Nexus7.2)',
          'luci.webrtc.perf/Perf Android32 (N Nexus6)',
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
        'testing': {'platform': 'linux'},
        'archive_apprtc': True,
        'swarming_dimensions': {
          'device_type': 'bullhead', # Nexus 5X
          'device_os': 'MMB29Q', # 6.0.1
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
        'testing': {'platform': 'linux'},
        'archive_apprtc': True,
        'swarming_dimensions': {
          'device_type': 'bullhead', # Nexus 5X
          'device_os': 'MMB29Q', # 6.0.1
          'os': 'Android',
          'android_devices': '1',
        }
      },
      'Android64 Builder arm64': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'binary_size_files': [
          'libjingle_peerconnection_so.so',
          'apks/AppRTCMobile.apk'
        ],
        'triggers': [
          'luci.webrtc.perf/Perf Android64 (L Nexus9)',
          'luci.webrtc.perf/Perf Android64 (N Pixel)',
        ],
      },
    },
  },
  'luci.webrtc.perf': {
    'settings': {
      'mastername': 'client.webrtc.perf',
      'build_gs_bucket': 'chromium-webrtc',
    },
    'builders': {
      'Perf Win7': {
        'recipe_config': 'webrtc_desktop_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'perf_id': 'webrtc-win-large-tests',
        'bot_type': 'tester',
        'parent_buildername': 'Win32 Builder (Clang)',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'gpu': None,
          'os': 'Windows',
        },
        'swarming_timeout': 7200,  # 2h
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
        'testing': {'platform': 'mac'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'gpu': None,
          'os': 'Mac-10.12',
        },
        'swarming_timeout': 7200,  # 2h
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'gpu': None,
          'os': 'Ubuntu-14.04',
        },
        'swarming_timeout': 7200,  # 2h
      },
      'Perf Linux Xenial': {
        'recipe_config': 'webrtc_desktop_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'perf_id': 'webrtc-linux-large-tests',
        'bot_type': 'tester',
        'parent_buildername': 'Linux64 Builder',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'gpu': None,
          'os': 'Ubuntu-16.04',
        },
        'swarming_timeout': 7200,  # 2h
      },
      'Perf Android32 (L Nexus4)': {
        'recipe_config': 'webrtc_android_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'perf_id': 'webrtc-android-tests-nexus4-lollipop',
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder arm',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'os': 'Android',
          'android_devices': '1',
          'device_type': 'mako', # Nexus 4
          'device_os': 'L',
        },
        'swarming_timeout': 7200,  # 2h
      },
      'Perf Android32 (K Nexus5)': {
        'recipe_config': 'webrtc_android_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'perf_id': 'webrtc-android-tests-nexus5-kitkat',
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder arm',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'os': 'Android',
          'android_devices': '1',
          'device_type': 'hammerhead', # Nexus 5
          'device_os': 'K',
        },
        'swarming_timeout': 7200,  # 2h
      },
      'Perf Android32 (L Nexus5)': {
        'recipe_config': 'webrtc_android_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'perf_id': 'webrtc-android-tests-nexus5',
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder arm',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'os': 'Android',
          'android_devices': '1',
          'device_type': 'hammerhead', # Nexus 5
          'device_os': 'L',
        },
        'swarming_timeout': 7200,  # 2h
      },
      'Perf Android32 (L Nexus6)': {
        'recipe_config': 'webrtc_android_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'perf_id': 'webrtc-android-tests-nexus6-lollipop',
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder arm',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'os': 'Android',
          'android_devices': '1',
          'device_type': 'shamu', # Nexus 6
          'device_os': 'L',
        },
        'swarming_timeout': 7200,  # 2h
      },
      'Perf Android32 (L Nexus7.2)': {
        'recipe_config': 'webrtc_android_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'perf_id': 'webrtc-android-tests-nexus72',
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder arm',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'os': 'Android',
          'android_devices': '1',
          'device_type': 'flo', # Nexus 7
          'device_os': 'L',
        },
        'swarming_timeout': 7200,  # 2h
      },
      'Perf Android32 (N Nexus6)': {
        'recipe_config': 'webrtc_android_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'perf_id': 'webrtc-android-tests-nexus6-nougat',
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder arm',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'os': 'Android',
          'android_devices': '1',
          'device_type': 'shamu', # Nexus 6
          'device_os': 'N',
        },
        'swarming_timeout': 7200,  # 2h
      },
      'Perf Android64 (L Nexus9)': {
        'recipe_config': 'webrtc_android_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'perf_id': 'webrtc-android-tests-nexus9',
        'bot_type': 'tester',
        'parent_buildername': 'Android64 Builder arm64',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'os': 'Android',
          'android_devices': '1',
          'device_type': 'flounder', # Nexus 9
          'device_os': 'L',
        },
        'swarming_timeout': 7200,  # 2h
      },
      'Perf Android64 (N Pixel)': {
        'recipe_config': 'webrtc_android_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'perf_id': 'webrtc-android-tests-pixel-nougat',
        'bot_type': 'tester',
        'parent_buildername': 'Android64 Builder arm64',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'pool': 'WebRTC-perf',
          'os': 'Android',
          'android_devices': '1',
          'device_type': 'sailfish', # Pixel
          'device_os': 'N',
        },
        'swarming_timeout': 7200,  # 2h
      },
    },
  },
  'luci.webrtc.try': {
    'settings': {
      'mastername': 'tryserver.webrtc',
      'build_gs_bucket': 'chromium-webrtc',
    },
    'builders': {
      'win_compile_x86_msvc_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_x86_msvc_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_x64_msvc_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_x64_msvc_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_x86_msvc_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        }
      },
      'win_x86_msvc_rel': {
        'recipe_config': 'webrtc_and_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        },
        'baremetal_swarming_dimensions': {
          'pool': 'WebRTC-baremetal-try',
          'os': 'Windows',
          'gpu': None,
        }
      },
      'win_x64_msvc_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        }
      },
      'win_x64_msvc_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        }
      },
      'win_compile_x86_clang_dbg': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_x86_clang_rel': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_x64_clang_dbg': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_x64_clang_rel': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_x86_clang_dbg': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        },
      },
      'win_x86_clang_rel': {
        'recipe_config': 'webrtc_and_baremetal_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        },
        'baremetal_swarming_dimensions': {
          'pool': 'WebRTC-baremetal-try',
          'os': 'Windows',
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
        'testing': {'platform': 'win'},
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
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        },
      },
      'win_x64_uwp': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-10',
          'cpu': 'x86-64',
        }
      },
      'win_x64_clang_dbg_win8': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-8.1-SP0',
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
        'testing': {'platform': 'win'},
        'swarming_dimensions': {
          'os': 'Windows-10',
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
        'testing': {'platform': 'mac'},
      },
      'mac_compile_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'mac_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        }
      },
      'mac_rel': {
        'recipe_config': 'webrtc_and_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'swarming_dimensions': {
          'os': 'Mac-10.11',
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
        'testing': {'platform': 'mac'},
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        }
      },
      'linux_compile_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'linux_compile_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'binary_size_files': [
          'obj/libwebrtc.a'
        ],
      },
      'linux_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
          'cpu': 'x86-64',
        }
      },
      'linux_rel': {
        'recipe_config': 'webrtc_and_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
          'cpu': 'x86-64',
        },
        'baremetal_swarming_dimensions': {
          'pool': 'WebRTC-baremetal-try',
          'os': 'Linux',
          'gpu': None,
        }
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
      },
      'linux_x86_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
      },
      'linux_asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan', 'lsan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
          'cpu': 'x86-64',
        }
      },
      'linux_compile_gcc_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'os': 'Ubuntu-16.04',
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
        'testing': {'platform': 'linux'},
      },
      'android_compile_arm_rel': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'binary_size_files': [
          'libjingle_peerconnection_so.so',
          'apks/AppRTCMobile.apk'
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
        'testing': {'platform': 'linux'},
      },
      'android_compile_arm64_rel': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'binary_size_files': [
          'libjingle_peerconnection_so.so',
          'apks/AppRTCMobile.apk'
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'device_type': 'bullhead', # Nexus 5X
          'device_os': 'MMB29Q', # 6.0.1
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
        'testing': {'platform': 'linux'},
        'build_android_archive': True,
        # TODO(bugs.webrtc.org/8642): Re-enable when it is fixed and stable.
        # 'test_android_studio_project_generation': True,
        'swarming_dimensions': {
          'device_type': 'bullhead', # Nexus 5X
          'device_os': 'MMB29Q', # 6.0.1
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'device_type': 'bullhead', # Nexus 5X
          'device_os': 'MMB29Q', # 6.0.1
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
        'testing': {'platform': 'linux'},
        'swarming_dimensions': {
          'device_type': 'bullhead', # Nexus 5X
          'device_os': 'MMB29Q', # 6.0.1
          'os': 'Android',
          'android_devices': '1',
        }
      },
      'android_experimental': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'test_android_studio_project_generation': True,
        'swarming_dimensions': {
          'device_type': 'bullhead', # Nexus 5X
          'device_os': 'MMB29Q', # 6.0.1
          'os': 'Android',
          'android_devices': '1',
        }
      },
    },
  },
})

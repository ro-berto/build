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
  'webrtc_baremetal': {
    'chromium_config': 'webrtc_default',
    'gclient_config': 'webrtc_with_limited',
    'test_suite': 'webrtc_baremetal',
  },
  'webrtc_desktop_perf_swarming': {
    'chromium_config': 'webrtc_desktop_perf',
    'gclient_config': 'webrtc',
    'test_suite': 'desktop_perf_swarming',
  },
  'webrtc_clang': {
    'chromium_config': 'webrtc_clang',
    'gclient_config': 'webrtc',
    'test_suite': 'webrtc',
  },
  'webrtc_android': {
    'chromium_config': 'android',
    'chromium_android_config': 'webrtc',
    'gclient_config': 'webrtc',
    'gclient_apply_config': ['android'],
    'test_suite': 'android',
  },
  'webrtc_android_perf': {
    'chromium_config': 'webrtc_android_perf',
    'chromium_android_config': 'webrtc',
    'gclient_config': 'webrtc',
    'gclient_apply_config': ['android'],
    'test_suite': 'android_perf',
  },
  'webrtc_android_perf_swarming': {
    'chromium_config': 'webrtc_android_perf',
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
  'client.webrtc': {
    'settings': {
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        }
      },
      'Win32 Release': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'binary_size_files': [
          'webrtc_perf_tests.exe'
        ],
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        }
      },
      'Win64 Debug': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['static_library'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
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
        'use_isolate': True,
        'enable_swarming': True,
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
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
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
      'Win32 Release [large tests]': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win32 ASan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
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
        'testing': {'platform': 'mac'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        }
      },
      'Mac64 Release': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        }
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        }
      },
      'Mac64 Release [large tests]': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'Linux32 Debug': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
      'Linux64 Release': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'binary_size_files': [
          'webrtc_perf_tests'
        ],
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
      'Linux MSan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['msan', 'msan_full_origin_tracking',
                                  'prebuilt_instrumented_libraries'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
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
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
      'Linux64 Release [large tests]': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
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
        'enable_swarming': True,
        'use_isolate': True,
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
        'enable_swarming': True,
        'use_isolate': True,
        'swarming_dimensions': {
          'device_os': 'MMB29Q', # 6.0.1
          'device_type': 'bullhead', # Nexus 5X
          'os': 'Android',
          'android_devices': '1',
        }
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
        'enable_swarming': True,
        'use_isolate': True,
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
        'binary_size_files': [
          'libjingle_peerconnection_so.so',
          'libjingle_peerconnection_datachannelonly_so.so',
          'apks/AppRTCMobile.apk'
        ],
        'archive_apprtc': True,
        'enable_swarming': True,
        'use_isolate': True,
        'swarming_dimensions': {
          'device_type': 'bullhead', # Nexus 5X
          'device_os': 'MMB29Q', # 6.0.1
          'os': 'Android',
          'android_devices': '1',
        }
      },
    },
  },
  'client.webrtc.branches': {
    'settings': {
      'build_gs_bucket': 'chromium-webrtc',
    },
    'builders': {
      'Win (stable)': {  # Win32 Release
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        }
      },
      'Win (beta)': {  # Win32 Release
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        }
      },
      'Mac (stable)': {  # Mac64 Release
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Mac-10.12',
          'cpu': 'x86-64',
        }
      },
      'Mac (beta)': {  # Mac64 Release
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Mac-10.12',
          'cpu': 'x86-64',
        }
      },
      'Linux (stable)': {  # Linux64 Release
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
      'Linux (beta)': {  # Linux64 Release
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
    },
  },
  'client.webrtc.fyi': {
    'settings': {
      'build_gs_bucket': 'chromium-webrtc',
    },
    'builders':  {
      'Win64 Debug (Win8)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-8.1-SP0',
          'cpu': 'x86-64',
        }
      },
      'Win64 Debug (Win10)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-10',
          'cpu': 'x86-64',
        }
      },
      'Android ASan (swarming)': {
        'recipe_config': 'webrtc_android_asan',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Android',
          'android_devices': '1',
          'device_type': 'bullhead', # Nexus 5X
        }
      },
      'Android Perf (swarming)': {
        'recipe_config': 'webrtc_android_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-swarming',
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Android',
          'android_devices': '1',
          'device_os': 'MMB29Q', # 6.0.1
        }
      },
    },
  },
  'client.webrtc.perf': {
    'settings': {
      'build_gs_bucket': 'chromium-webrtc',
    },
    'builders': {
       'Win7': {
        'recipe_config': 'webrtc_desktop_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-win-large-tests',
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'pool': 'WebRTC',
          'gpu': None,
          'os': 'Windows',
          'id': 'build18-m3',
        },
        'swarming_timeout': 3600,  # 1h
      },
      'Mac 10.11': {
        'recipe_config': 'webrtc_desktop_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-mac-large-tests',
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'pool': 'WebRTC',
          'gpu': None,
          'os': 'Mac-10.12',
          'id': 'build16-m3',
        },
        'swarming_timeout': 3600,  # 1h
      },
      'Linux Trusty': {
        'recipe_config': 'webrtc_desktop_perf_swarming',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-linux-large-tests',
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'pool': 'WebRTC',
          'gpu': None,
          'os': 'Ubuntu-14.04',
          'id': 'build17-m3',
        },
        'swarming_timeout': 3600,  # 1h
      },
      'Android32 Builder': {
        'recipe_config': 'webrtc_android_perf',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'triggers': [
          'Android32 Tests (K Nexus5)',
          'Android32 Tests (L Nexus4)',
          'Android32 Tests (L Nexus5)',
          'Android32 Tests (L Nexus6)',
          'Android32 Tests (L Nexus7.2)',
          'Android32 Tests (N Nexus6)',
        ],
      },
      'Android64 Builder': {
        'recipe_config': 'webrtc_android_perf',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'triggers': [
          'Android64 Tests (L Nexus9)',
          'Android64 Tests (N Pixel)',
        ],
      },
      'Android32 Tests (L Nexus4)': {
        'recipe_config': 'webrtc_android_perf',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus4-lollipop',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (K Nexus5)': {
        'recipe_config': 'webrtc_android_perf',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus5-kitkat',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (L Nexus5)': {
        'recipe_config': 'webrtc_android_perf',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus5',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (L Nexus6)': {
        'recipe_config': 'webrtc_android_perf',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus6-lollipop',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (L Nexus7.2)': {
        'recipe_config': 'webrtc_android_perf',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus72',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder Release',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (N Nexus6)': {
        'recipe_config': 'webrtc_android_perf',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus6-nougat',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder Release',
        'testing': {'platform': 'linux'},
      },
      'Android64 Tests (L Nexus9)': {
        'recipe_config': 'webrtc_android_perf',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus9',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android64 Builder',
        'testing': {'platform': 'linux'},
      },
      'Android64 Tests (N Pixel)': {
        'recipe_config': 'webrtc_android_perf',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-pixel-nougat',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android64 Builder',
        'testing': {'platform': 'linux'},
      },
    },
  },
  'tryserver.webrtc': {
    'settings': {
      'build_gs_bucket': 'chromium-webrtc',
    },
    'builders': {
      'win_compile_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_x64_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_x64_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        }
      },
      'win_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
        }
      },
      'win_x64_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        }
      },
      'win_x64_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        }
      },
      'win_clang_dbg': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_clang_rel': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_x64_clang_dbg': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_x64_clang_rel': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_baremetal': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86-64',
        }
      },
      'win_x64_win8': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-8.1-SP0',
          'cpu': 'x86-64',
        }
      },
      'win_x64_win10': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-10',
          'cpu': 'x86-64',
        }
      },
      'win_experimental': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Windows-7-SP1',
          'cpu': 'x86',
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        }
      },
      'mac_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        }
      },
      'mac_baremetal': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
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
      'mac_experimental': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Mac-10.11',
          'cpu': 'x86-64',
        }
      },
      'linux_compile_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'linux_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
      'linux_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
      'linux_arm64_dbg': {
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
      'linux_arm64_rel': {
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
      'linux32_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86',
        }
      },
      'linux32_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86',
        }
      },
      'linux32_arm_dbg': {
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
      'linux32_arm_rel': {
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
      'linux_gcc_rel': {
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
      'linux_msan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['msan', 'msan_full_origin_tracking',
                                  'prebuilt_instrumented_libraries'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
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
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
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
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
      'linux_baremetal': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_experimental': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'os': 'Ubuntu-14.04',
          'cpu': 'x86-64',
        }
      },
      'android_compile_dbg': {
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
      'android_compile_rel': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
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
      'android_compile_mips_dbg': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'mipsel',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_dbg': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
        'swarming_dimensions': {
          'device_type': 'bullhead', # Nexus 5X
          'device_os': 'MMB29Q', # 6.0.1
          'os': 'Android',
          'android_devices': '1',
        }
      },
      'android_rel': {
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
        'use_isolate': True,
        'enable_swarming': True,
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
        'binary_size_files': [
          'libjingle_peerconnection_so.so',
          'libjingle_peerconnection_datachannelonly_so.so',
          'apks/AppRTCMobile.apk'
        ],
        'use_isolate': True,
        'enable_swarming': True,
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
        'use_isolate': True,
        'enable_swarming': True,
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

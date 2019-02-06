# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SPEC = {
  'settings': {
      'build_gs_bucket': 'chromium-webrtc'
  },
  'builders': {
    'WebRTC Chromium FYI Android Builder': {
      'android_config': 'base_config',
      'bot_type': 'builder_tester',
      'chromium_apply_config': ['dcheck', 'mb', 'android'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android'
      },
      'gclient_apply_config': ['android'],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'linux'
      }
    },
    'WebRTC Chromium FYI Android Builder (dbg)': {
      'android_config': 'base_config',
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb', 'android'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android'
      },
      'gclient_apply_config': ['android'],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'linux'
      }
    },
    'WebRTC Chromium FYI Android Builder ARM64 (dbg)': {
      'android_config': 'base_config',
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb', 'android'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android'
      },
      'gclient_apply_config': ['android'],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'linux'
      }
    },
    'WebRTC Chromium FYI Android Tests (dbg) (K Nexus5)': {
      'android_config': 'base_config',
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb', 'android'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 32,
        'TARGET_PLATFORM': 'android'
      },
      'gclient_apply_config': ['android'],
      'gclient_config': 'chromium_webrtc_tot',
      'parent_buildername': 'WebRTC Chromium FYI Android Builder (dbg)',
      'root_devices': True,
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux'
      },
    },
    'WebRTC Chromium FYI Android Tests (dbg) (M Nexus5X)': {
      'android_config': 'base_config',
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb', 'android'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android'
      },
      'gclient_apply_config': ['android'],
      'gclient_config': 'chromium_webrtc_tot',
      'parent_buildername': 'WebRTC Chromium FYI Android Builder ARM64 (dbg)',
      'root_devices': True,
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux'
      },
    },
    'WebRTC Chromium FYI Linux Builder': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': ['webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'linux'
      }
    },
    'WebRTC Chromium FYI Linux Builder (RBE)': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'goma_rbe_prod', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'linux'
      }
    },
    'WebRTC Chromium FYI Linux Builder (dbg)': {
      'bot_type': 'builder_tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'linux'
      }
    },
    'WebRTC Chromium FYI Linux Builder (dbg) (RBE)': {
      'bot_type': 'builder_tester',
      'chromium_apply_config': ['dcheck', 'goma_rbe_prod', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'linux'
      }
    },
    'WebRTC Chromium FYI Linux Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc_tot',
      'parent_buildername': 'WebRTC Chromium FYI Linux Builder',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'linux'
      },
    },
    'WebRTC Chromium FYI Mac Builder': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': ['webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'mac'
      }
    },
    'WebRTC Chromium FYI Mac Builder (dbg)': {
      'bot_type': 'builder_tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'mac'
      }
    },
    'WebRTC Chromium FYI Mac Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc_tot',
      'parent_buildername': 'WebRTC Chromium FYI Mac Builder',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'mac'
      },
    },
    'WebRTC Chromium FYI Win Builder': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': ['webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'win'
      }
    },
    'WebRTC Chromium FYI Win Builder (dbg)': {
      'bot_type': 'builder_tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Debug',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc_tot',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'testing': {
        'platform': 'win'
      }
    },
    'WebRTC Chromium FYI Win10 Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc_tot',
      'parent_buildername': 'WebRTC Chromium FYI Win Builder',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'win'
      },
    },
    'WebRTC Chromium FYI Win7 Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc_tot',
      'parent_buildername': 'WebRTC Chromium FYI Win Builder',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'win'
      },
    },
    'WebRTC Chromium FYI Win8 Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc_tot',
      'parent_buildername': 'WebRTC Chromium FYI Win Builder',
      'set_component_rev': {
        'name': 'src/third_party/webrtc',
        'rev_str': '%s'
      },
      'test_results_config': 'public_server',
      'testing': {
        'platform': 'win'
      },
    }
  },
}

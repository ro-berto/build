# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
  'settings': { 'build_gs_bucket': 'chromium-webrtc'},
  'builders': {
    'WebRTC Chromium Android Builder': {
      'android_config': 'base_config',
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb', 'android'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android'
      },
      'gclient_apply_config': ['android'],
      'gclient_config': 'chromium_webrtc',
      'testing': { 'platform': 'linux'}
    },
    'WebRTC Chromium Android Tester': {
      'android_config': 'base_config',
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb', 'android'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_ARCH': 'arm',
        'TARGET_BITS': 64,
        'TARGET_PLATFORM': 'android'
      },
      'gclient_apply_config': ['android'],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'WebRTC Chromium Android Builder',
      'root_devices': True,
      'swarming_dimensions': {
        'device_os': 'MMB29Q',
        'device_type': 'bullhead',
        'os': 'Android'
      },
      'test_results_config': 'public_server',
      'testing': { 'platform': 'linux'},
    },
    'WebRTC Chromium Linux Builder': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': ['webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc',
      'testing': { 'platform': 'linux'}
    },
    'WebRTC Chromium Linux Builder (RBE)': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'goma_rbe_prod', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc',
      'testing': { 'platform': 'linux'}
    },
    'WebRTC Chromium Linux Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'WebRTC Chromium Linux Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'linux'},
    },
    'WebRTC Chromium Mac Builder': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': ['webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc',
      'testing': { 'platform': 'mac'}
    },
    'WebRTC Chromium Mac Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 64
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'WebRTC Chromium Mac Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'mac'},
    },
    'WebRTC Chromium Win Builder': {
      'bot_type': 'builder',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': ['webrtc_test_resources'],
      'gclient_config': 'chromium_webrtc',
      'testing': { 'platform': 'win'}
    },
    'WebRTC Chromium Win10 Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'WebRTC Chromium Win Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'win'},
    },
    'WebRTC Chromium Win7 Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'WebRTC Chromium Win Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'win'},
    },
    'WebRTC Chromium Win8 Tester': {
      'bot_type': 'tester',
      'chromium_apply_config': ['dcheck', 'mb'],
      'chromium_config': 'chromium',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32
      },
      'gclient_apply_config': [],
      'gclient_config': 'chromium_webrtc',
      'parent_buildername': 'WebRTC Chromium Win Builder',
      'test_results_config': 'public_server',
      'testing': { 'platform': 'win'},
    }
  },
}

# TODO(crbug.com/888429): Add this test through test_suites.pyl instead.
# The problem is that our performance-reporting gtest doesn't report results.
BAREMETAL_BROWSER_TESTS_FILTER = [
  # Runs hardware-exercising test.
  'WebRtcWebcamBrowserTests*',
]

PERF_BROWSER_TESTS_FILTER = [
  'WebRtcInternalsPerfBrowserTest.*',
  'WebRtcStatsPerfBrowserTest.*',
  'WebRtcVideoDisplayPerfBrowserTests*',
  'WebRtcVideoQualityBrowserTests*',
]

def browser_perf_test(perf_id):
  return steps.WebRTCPerfTest(
      name='browser_tests',
      # These tests needs --test-launcher-jobs=1 since some of them are
      # not able to run in parallel (they record system audio, etc).
      args=['--gtest_filter=%s' % ':'.join(
                BAREMETAL_BROWSER_TESTS_FILTER + PERF_BROWSER_TESTS_FILTER
            ),
            '--run-manual', '--ui-test-action-max-timeout=350000',
            '--test-launcher-jobs=1',
            '--test-launcher-bot-mode',
            '--test-launcher-print-test-stdio=always'],
      perf_id=perf_id,
      perf_config_mappings=None,
      commit_position_property='got_revision_cp')

SPEC['builders']['WebRTC Chromium Linux Tester']['tests'] = [
  browser_perf_test('chromium-webrtc-rel-linux')
]
SPEC['builders']['WebRTC Chromium Mac Tester']['tests'] = [
  browser_perf_test('chromium-webrtc-rel-mac')
]
SPEC['builders']['WebRTC Chromium Win10 Tester']['tests'] = [
  browser_perf_test('chromium-webrtc-rel-win10')
]
SPEC['builders']['WebRTC Chromium Win7 Tester']['tests'] = [
  browser_perf_test('chromium-webrtc-rel-7')
]
SPEC['builders']['WebRTC Chromium Win8 Tester']['tests'] = [
  browser_perf_test('chromium-webrtc-rel-win8')
]

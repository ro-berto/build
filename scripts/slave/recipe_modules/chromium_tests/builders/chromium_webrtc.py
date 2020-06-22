# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from .. import bot_spec, steps

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
    'WebRtcVideoHighBitrateBrowserTest*',
    'WebRtcVideoQualityBrowserTests*',
]


def browser_perf_test(perf_id):
  return bot_spec.TestSpec.create(
      steps.WebRTCPerfTest,
      name='browser_tests',
      # These tests needs --test-launcher-jobs=1 since some of them are
      # not able to run in parallel (they record system audio, etc).
      args=[
          '--gtest_filter=%s' %
          ':'.join(BAREMETAL_BROWSER_TESTS_FILTER + PERF_BROWSER_TESTS_FILTER),
          '--run-manual', '--ui-test-action-max-timeout=300000',
          '--test-launcher-timeout=350000', '--test-launcher-jobs=1',
          '--test-launcher-bot-mode', '--test-launcher-print-test-stdio=always'
      ],
      perf_id=perf_id,
      commit_position_property='got_revision_cp')


def _chromium_webrtc_spec(**kwargs):
  return bot_spec.BotSpec.create(build_gs_bucket='chromium-webrtc', **kwargs)


SPEC = {
    'WebRTC Chromium Android Builder':
        _chromium_webrtc_spec(
            android_config='base_config',
            chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth', 'android'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android'
            },
            gclient_apply_config=['android'],
            gclient_config='chromium_webrtc',
            simulation_platform='linux',
        ),
    'WebRTC Chromium Android Tester':
        _chromium_webrtc_spec(
            android_config='base_config',
            execution_mode=bot_spec.TEST,
            chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth', 'android'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_ARCH': 'arm',
                'TARGET_BITS': 64,
                'TARGET_PLATFORM': 'android'
            },
            gclient_apply_config=['android'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Android Builder',
            swarming_dimensions={
                'device_os': 'MMB29Q',
                'device_type': 'bullhead',
                'os': 'Android'
            },
            test_results_config='public_server',
            simulation_platform='linux',
        ),
    'WebRTC Chromium Linux Builder':
        _chromium_webrtc_spec(
            chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            simulation_platform='linux',
        ),
    'WebRTC Chromium Linux Tester':
        _chromium_webrtc_spec(
            execution_mode=bot_spec.TEST,
            chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Linux Builder',
            test_results_config='public_server',
            simulation_platform='linux',
            test_specs=[browser_perf_test('chromium-webrtc-rel-linux')],
        ),
    'WebRTC Chromium Mac Builder':
        _chromium_webrtc_spec(
            chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            simulation_platform='mac',
        ),
    'WebRTC Chromium Mac Tester':
        _chromium_webrtc_spec(
            execution_mode=bot_spec.TEST,
            chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 64
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Mac Builder',
            test_results_config='public_server',
            simulation_platform='mac',
            test_specs=[browser_perf_test('chromium-webrtc-rel-mac')],
        ),
    'WebRTC Chromium Win Builder':
        _chromium_webrtc_spec(
            chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            simulation_platform='win',
        ),
    'WebRTC Chromium Win10 Tester':
        _chromium_webrtc_spec(
            execution_mode=bot_spec.TEST,
            chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Win Builder',
            test_results_config='public_server',
            simulation_platform='win',
            test_specs=[browser_perf_test('chromium-webrtc-rel-win10')],
        ),
    'WebRTC Chromium Win7 Tester':
        _chromium_webrtc_spec(
            execution_mode=bot_spec.TEST,
            chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Win Builder',
            test_results_config='public_server',
            simulation_platform='win',
            test_specs=[browser_perf_test('chromium-webrtc-rel-7')],
        ),
    'WebRTC Chromium Win8 Tester':
        _chromium_webrtc_spec(
            execution_mode=bot_spec.TEST,
            chromium_apply_config=['dcheck', 'mb', 'mb_luci_auth'],
            chromium_config='chromium',
            chromium_config_kwargs={
                'BUILD_CONFIG': 'Release',
                'TARGET_BITS': 32
            },
            gclient_apply_config=['webrtc_test_resources'],
            gclient_config='chromium_webrtc',
            parent_buildername='WebRTC Chromium Win Builder',
            test_results_config='public_server',
            simulation_platform='win',
            test_specs=[browser_perf_test('chromium-webrtc-rel-win8')],
        ),
}

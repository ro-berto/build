# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
from . import steps


_builders = collections.defaultdict(dict)


SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-webrtc',
  },
  'builders': {},
}

BROWSER_TESTS_FILTER = [
  # Benefits from non-default device configurations (but could be implemented
  # on a VM using the fake device flags in different combinations)..
  'MediaStreamDevicesControllerTest.*',
  'MediaStreamDevicesControllerBrowserTestInstance*',

  # Runs hardware-exercising test and/or video calling tests.
  'WebRtcApprtcBrowserTest.*',
  'WebrtcAudioPrivateTest.*',
  'WebRtcAudioQualityBrowserTest.*',
  'WebRtcBrowserTest.*',
  'WebRtcDisableEncryptionFlagBrowserTest.*',
  'WebRtcGetMediaDevicesBrowserTests*',
  'WebRtcInternalsPerfBrowserTest.*',
  'WebRtcMediaRecorderTest.*',
  'WebRtcSimulcastBrowserTest.*',
  'WebRtcStatsPerfBrowserTest.*',
  'WebRtcVideoQualityBrowserTests*',
  'WebRtcWebcamBrowserTests*',
]


def BaseSpec(bot_type, chromium_apply_config, gclient_config, platform,
             target_bits, build_config='Release'):
  spec = {
    'bot_type': bot_type,
    'chromium_apply_config' : chromium_apply_config,
    'chromium_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': build_config,
      'TARGET_BITS': target_bits,
    },
    'gclient_config': gclient_config,
    'gclient_apply_config': [],
    'testing': {
      'platform': 'linux' if platform == 'android' else platform,
    },
  }
  spec['chromium_apply_config'].append('chrome_with_codecs')
  if platform == 'android':
    spec['android_config'] = 'base_config'
    spec['chromium_config_kwargs']['TARGET_ARCH'] = 'arm'
    spec['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
    spec['chromium_apply_config'].append('android')
    spec['gclient_apply_config'].append('android')
  return spec


def BuildSpec(platform, target_bits, build_config='Release',
              gclient_config='chromium_webrtc'):
  spec = BaseSpec(
      bot_type='builder',
      chromium_apply_config=['dcheck', 'blink_logging_on', 'mb'],
      gclient_config=gclient_config,
      platform=platform,
      target_bits=target_bits,
      build_config=build_config)
  return spec


def TestSpec(parent_builder, perf_id, platform, target_bits,
             build_config='Release', perf_config_mappings=None,
             commit_position_property='got_revision_cp',
             gclient_config='chromium_webrtc',
             test_spec_file='chromium.webrtc.json'):
  spec = BaseSpec(
      bot_type='tester',
      chromium_apply_config=[],
      gclient_config=gclient_config,
      platform=platform,
      target_bits=target_bits,
      build_config=build_config)

  spec['parent_buildername'] = parent_builder
  spec['test_results_config'] = 'public_server'

  if platform == 'android':
    spec['root_devices'] = True
    spec['tests'] = [
      steps.GTestTest(
          'content_browsertests',
          args=['--gtest_filter=WebRtc*']),
    ]
  else:
    spec['gclient_apply_config'].append('webrtc_test_resources')
    if perf_id.endswith('-long'):
      pass  # Not implemented yet (see crbug.com/723989).
    else:
      spec['tests'] = [
        steps.GTestTest(
            'content_browsertests',
            # Run all normal WebRTC content_browsertests. This is mostly so
            # the FYI bots can detect breakages.
            args=['--gtest_filter=WebRtc*']),
        steps.GTestTest(
            name='content_browsertests (manual)',
            target_name='content_browsertests',
            # These run a few tests that require webcam access. They need to
            # run sequentially, otherwise tests may interfere with each other.
            args=['--gtest_filter=WebRtc*MANUAL*', '--run-manual',
                  '--test-launcher-jobs=1', '--test-launcher-bot-mode']),
        steps.WebRTCPerfTest(
            'browser_tests',
            # These tests needs --test-launcher-jobs=1 since some of them are
            # not able to run in parallel (they record system audio, etc).
            args=['--gtest_filter=%s' % ':'.join(BROWSER_TESTS_FILTER),
                  '--run-manual', '--ui-test-action-max-timeout=350000',
                  '--test-launcher-jobs=1',
                  '--test-launcher-bot-mode',
                  '--test-launcher-print-test-stdio=always'],
            perf_id=perf_id,
            perf_config_mappings=perf_config_mappings,
            commit_position_property=commit_position_property,
            upload_wav_files_from_test=True),

        # Run capture unittests as well since our bots have real webcams.
        steps.GTestTest('capture_unittests',
                   args=['--enable-logging',
                         '--v=1',
                         '--test-launcher-jobs=1',
                         '--test-launcher-print-test-stdio=always']),
        steps.GTestTest('content_unittests'),
        steps.GTestTest('jingle_unittests'),
        steps.GTestTest('remoting_unittests', args=['--gtest_filter=Webrtc*']),
      ]
  return spec


def AddBuildSpec(name, platform, target_bits=64):
  SPEC['builders'][name] = BuildSpec(platform, target_bits)
  assert target_bits not in _builders[platform]
  _builders[platform][target_bits] = name


def AddTestSpec(name, perf_id, platform, target_bits=64):
  parent_builder = _builders[platform][target_bits]
  SPEC['builders'][name] = TestSpec(parent_builder, perf_id, platform,
                                    target_bits)


AddBuildSpec('Win Builder', 'win', target_bits=32)
AddBuildSpec('Mac Builder', 'mac')
AddBuildSpec('Linux Builder', 'linux')

AddTestSpec('Win7 Tester', 'chromium-webrtc-rel-7', 'win', target_bits=32)
AddTestSpec('Win7 Tester (long-running)', 'chromium-webrtc-rel-7-long', 'win',
            target_bits=32)
AddTestSpec('Win8 Tester', 'chromium-webrtc-rel-win8', 'win', target_bits=32)
AddTestSpec('Win10 Tester', 'chromium-webrtc-rel-win10', 'win', target_bits=32)
AddTestSpec('Mac Tester', 'chromium-webrtc-rel-mac', 'mac')
AddTestSpec('Mac Tester (long-running)', 'chromium-webrtc-rel-mac-long', 'mac')
AddTestSpec('Linux Tester', 'chromium-webrtc-rel-linux', 'linux')

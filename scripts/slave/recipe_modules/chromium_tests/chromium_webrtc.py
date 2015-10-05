# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
from . import steps


_builders = collections.defaultdict(dict)


SPEC = {
  'builders': {},
  'settings': {
    'build_gs_bucket': 'chromium-webrtc',
  },
}


def BaseSpec(bot_type, chromium_apply_config, gclient_config, platform,
             target_bits, perf_id=None, build_config='Release'):
  spec = {
    'bot_type': bot_type,
    'chromium_apply_config' : chromium_apply_config,
    'chromium_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': build_config,
      'TARGET_BITS': target_bits,
    },
    'gclient_config': 'chromium_webrtc',
    'testing': {
      'platform': 'linux' if platform == 'android' else platform,
    },
  }
  if platform == 'android':
    spec['android_config'] = 'base_config'
    spec['chromium_config_kwargs']['TARGET_ARCH'] = 'arm'
    spec['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
    spec['chromium_apply_config'].append('android')
    spec['gclient_apply_config'] = ['android']

  if perf_id:
    spec['perf-id'] = perf_id
  return spec


def BuildSpec(platform, target_bits, perf_id=None, build_config='Release',
              gclient_config='chromium_webrtc'):
  spec = BaseSpec(
      bot_type='builder',
      chromium_apply_config=['dcheck', 'blink_logging_on'],
      gclient_config=gclient_config,
      platform=platform,
      target_bits=target_bits,
      perf_id=perf_id,
      build_config=build_config)

  if platform == 'android':
    spec['compile_targets'] = ['android_builder_chromium_webrtc']
  else:
    spec['compile_targets'] = ['chromium_builder_webrtc']
  return spec


def TestSpec(parent_builder, perf_id, platform, target_bits,
             disable_runhooks=False, build_config='Release',
             gclient_config='chromium_webrtc',
             test_spec_file='chromium.webrtc.json'):
  spec = BaseSpec(
      bot_type='tester',
      chromium_apply_config=[],
      gclient_config=gclient_config,
      platform=platform,
      target_bits=target_bits,
      perf_id=perf_id,
      build_config=build_config)

  spec['parent_buildername'] = parent_builder
  spec['results-url'] = 'https://chromeperf.appspot.com'

  # TODO(kjellander): Re-enable hooks everywhere on as soon we've moved away
  # from downloading test resources in that step. It would ideally be done as a
  # separate build step instead of relying on the webrtc.DEPS solution.
  if disable_runhooks:
    spec['disable_runhooks'] = True

  spec['test_generators'] = [
    steps.generate_gtest,
    steps.generate_script,
    steps.generate_isolated_script,
  ]

  if platform == 'android':
    spec['root_devices'] = True
    spec['tests'] = [
      steps.GTestTest(
          'content_browsertests',
          args=['--gtest_filter=WebRtc*'],
          android_isolate_path='content/content_browsertests.isolate'),
    ]
  else:
    spec['test_spec_file'] = test_spec_file
  return spec


def AddBuildSpec(name, platform, target_bits=64):
  SPEC['builders'][name] = BuildSpec(platform, target_bits)
  assert target_bits not in _builders[platform]
  _builders[platform][target_bits] = name


def AddTestSpec(name, perf_id, platform, target_bits=64,
                disable_runhooks=False):
  parent_builder = _builders[platform][target_bits]
  SPEC['builders'][name] = TestSpec(parent_builder, perf_id, platform,
                                    target_bits, disable_runhooks)


AddBuildSpec('Win Builder', 'win', target_bits=32)
AddBuildSpec('Mac Builder', 'mac')
AddBuildSpec('Linux Builder', 'linux')

AddTestSpec('WinXP Tester', 'chromium-webrtc-rel-xp', 'win', target_bits=32,
            disable_runhooks=True)
AddTestSpec('Win7 Tester', 'chromium-webrtc-rel-7', 'win', target_bits=32)
AddTestSpec('Win8 Tester', 'chromium-webrtc-rel-win7', 'win', target_bits=32)
AddTestSpec('Win10 Tester', 'chromium-webrtc-rel-win10', 'win', target_bits=32)
AddTestSpec('Mac Tester', 'chromium-webrtc-rel-mac', 'mac')
AddTestSpec('Linux Tester', 'chromium-webrtc-rel-linux', 'linux')

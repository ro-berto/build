# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps


SPEC = {
  'builders': {},
  'settings': {
    'build_gs_bucket': 'chrome-perf',
  },
}


def _BaseSpec(bot_type, chromium_apply_config, disable_tests,
              gclient_config, platform, target_bits):
  return {
    'bot_type': bot_type,
    'chromium_apply_config' : chromium_apply_config,
    'chromium_config': 'chromium_official',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': target_bits,
    },
    'disable_tests': disable_tests,
    'gclient_config': gclient_config,
    'testing': {
      'platform': 'linux' if platform == 'android' else platform,
    },
  }


def _BuildSpec(platform, target_bits):
  spec = _BaseSpec(
      bot_type='builder',
      chromium_apply_config=['chromium_perf', 'goma_hermetic_fallback'],
      disable_tests=True,
      gclient_config='chromium',
      platform=platform,
      target_bits=target_bits)

  if platform == 'android':
    spec['chromium_apply_config'].append('android')
    spec['chromium_config_kwargs']['TARGET_ARCH'] = 'arm'
    spec['gclient_apply_config'] = ['android', 'perf']
  else:
    spec['compile_targets'] = ['chromium_builder_perf']
    spec['gclient_apply_config'] = ['chrome_internal']

  return spec


def _TestSpec(parent_builder, perf_id, platform, target_bits,
              shard_index, num_host_shards, num_device_shards):
  spec = _BaseSpec(
      bot_type='tester',
      chromium_apply_config=[],
      disable_tests=platform == 'android',
      gclient_config='perf',
      platform=platform,
      target_bits=target_bits)

  spec['parent_buildername'] = parent_builder
  spec['perf-id'] = perf_id
  spec['results-url'] = 'https://chromeperf.appspot.com'
  spec['tests'] = [
    steps.DynamicPerfTests(platform, target_bits, perf_id, shard_index,
                           num_host_shards, num_device_shards),
  ]

  if platform == 'android':
    spec['android_config'] = 'perf'
    spec['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
    spec['gclient_apply_config'] = ['android']
  else:
    spec['test_generators'] = [steps.generate_script]
    spec['test_spec_file'] = 'chromium.perf.json'

  return spec


def _AddBuildSpec(name, platform, target_bits=64):
  SPEC['builders'][name] = _BuildSpec(platform, target_bits)


def _AddTestSpec(name, parent_builder, perf_id, platform, target_bits=64,
                 num_host_shards=1, num_device_shards=1):
  if num_host_shards > 1:
    for shard_index in xrange(num_host_shards):
      builder_name = '%s (%d)' % (name, shard_index + 1)
      SPEC['builders'][builder_name] = _TestSpec(
          parent_builder, perf_id, platform, target_bits,
          shard_index, num_host_shards, num_device_shards)
  else:
    SPEC['builders'][name] = _TestSpec(
        parent_builder, perf_id, platform, target_bits,
        0, num_host_shards, num_device_shards)


_AddBuildSpec(
    name='Linux Builder',
    platform='linux')

_AddBuildSpec(
    name='Win Builder',
    platform='win',
    target_bits=32)

_AddBuildSpec(
    name='Win x64 Builder',
    platform='win')

_AddBuildSpec(
    name='Mac Builder',
    platform='mac')

_AddBuildSpec(
    name='Android Builder',
    platform='android',
    target_bits=32)

_AddBuildSpec(
    name='Android arm64 Builder',
    platform='android')


_AddTestSpec(
    name='Linux Perf',
    parent_builder='Linux Builder',
    perf_id='linux-release',
    platform='linux',
    num_host_shards=5)

_AddTestSpec(
    name='Win 8 Perf',
    parent_builder='Win x64 Builder',
    perf_id='chromium-rel-win8-dual',
    platform='win',
    num_host_shards=5)

_AddTestSpec(
    name='Win 7 Perf',
    parent_builder='Win Builder',
    perf_id='chromium-rel-win7-dual',
    platform='win',
    target_bits=32,
    num_host_shards=5)

_AddTestSpec(
    name='Win 7 x64 Perf',
    parent_builder='Win x64 Builder',
    perf_id='chromium-rel-win7-x64-dual',
    platform='win',
    num_host_shards=5)

_AddTestSpec(
    name='Win 7 ATI GPU Perf',
    parent_builder='Win x64 Builder',
    perf_id='chromium-rel-win7-gpu-ati',
    platform='win',
    num_host_shards=5)

_AddTestSpec(
    name='Win 7 Intel GPU Perf',
    parent_builder='Win x64 Builder',
    perf_id='chromium-rel-win7-gpu-intel',
    platform='win',
    num_host_shards=5)

_AddTestSpec(
    name='Win 7 Nvidia GPU Perf',
    parent_builder='Win x64 Builder',
    perf_id='chromium-rel-win7-gpu-nvidia',
    platform='win',
    num_host_shards=5)

_AddTestSpec(
    name='Win 7 Low-End Perf',
    parent_builder='Win Builder',
    perf_id='chromium-rel-win7-single',
    platform='win',
    target_bits=32,
    num_host_shards=2)

_AddTestSpec(
    name='Win XP Perf',
    parent_builder='Win Builder',
    perf_id='chromium-rel-xp-dual',
    platform='win',
    target_bits=32,
    num_host_shards=5)

_AddTestSpec(
    name='Mac 10.10 Perf',
    parent_builder='Mac Builder',
    perf_id='chromium-rel-mac10',
    platform='mac',
    num_host_shards=5)

_AddTestSpec(
    name='Mac 10.9 Perf',
    parent_builder='Mac Builder',
    perf_id='chromium-rel-mac9',
    platform='mac',
    num_host_shards=5)

_AddTestSpec(
    name='Android Nexus5 Perf',
    parent_builder='Android Builder',
    perf_id='android-nexus5',
    platform='android',
    target_bits=32,
    num_device_shards=8)

_AddTestSpec(
    name='Android Nexus6 Perf',
    parent_builder='Android Builder',
    perf_id='android-nexus6',
    platform='android',
    target_bits=32,
    num_device_shards=8)

_AddTestSpec(
    name='Android Nexus7v2 Perf',
    parent_builder='Android Builder',
    perf_id='android-nexus7v2',
    platform='android',
    target_bits=32,
    num_device_shards=8)

_AddTestSpec(
    name='Android Nexus9 Perf',
    parent_builder='Android arm64 Builder',
    perf_id='android-nexus9',
    platform='android',
    num_device_shards=8)

_AddTestSpec(
    name='Android One Perf',
    parent_builder='Android Builder',
    perf_id='android-one',
    platform='android',
    target_bits=32,
    num_device_shards=8)

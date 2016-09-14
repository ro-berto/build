# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

from . import steps

import DEPS
CHROMIUM_CONFIG_CTX = DEPS['chromium'].CONFIG_CTX
GCLIENT_CONFIG_CTX = DEPS['gclient'].CONFIG_CTX


builders = collections.defaultdict(dict)


SPEC = {
  'builders': {},
  'settings': {
    'build_gs_bucket': 'chrome-perf',
    # Bucket for storing builds for manual bisect
    'bisect_build_gs_bucket': 'chrome-test-builds',
    'bisect_build_gs_extra': 'official-by-commit',
    'bisect_builders': []
  },
}


@CHROMIUM_CONFIG_CTX(includes=['chromium', 'official', 'mb'])
def chromium_perf(c):
  c.clobber_before_runhooks = False
  pass


def _BaseSpec(bot_type, config_name, platform, target_bits, tests):
  spec = {
    'bot_type': bot_type,
    'chromium_config': config_name,
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': target_bits,
    },
    'gclient_config': config_name,
    'testing': {
      'platform': 'linux' if platform == 'android' else platform,
    },
    'tests': tests,
  }

  if platform == 'android':
    spec['android_config'] = 'chromium_perf'
    spec['chromium_apply_config'] = ['android']
    spec['chromium_config_kwargs']['TARGET_ARCH'] = 'arm'
    spec['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
    spec['gclient_apply_config'] = ['android']

  return spec


def BuildSpec(
  config_name, perf_id, platform, target_bits, enable_swarming=False):
  if platform == 'android':
    # TODO: Run sizes on Android.
    tests = []
  else:
    tests = [steps.SizesStep('https://chromeperf.appspot.com', perf_id)]

  spec = _BaseSpec(
      bot_type='builder',
      config_name=config_name,
      platform=platform,
      target_bits=target_bits,
      tests=tests,
  )

  if enable_swarming:
    spec['enable_swarming'] = True
    spec['use_isolate'] = True
  spec['compile_targets'] = ['chromium_builder_perf']

  return spec


def TestSpec(config_name, perf_id, platform, target_bits,
             parent_buildername=None, tests=None):
  spec = _BaseSpec(
      bot_type='tester',
      config_name=config_name,
      platform=platform,
      target_bits=target_bits,
      tests=tests or [],
  )

  if not parent_buildername:
    parent_buildername = builders[platform][target_bits]
  spec['parent_buildername'] = parent_buildername
  spec['perf-id'] = perf_id
  spec['results-url'] = 'https://chromeperf.appspot.com'
  spec['test_generators'] = [steps.generate_script]

  return spec


def _AddBuildSpec(
  name, platform, target_bits=64, add_to_bisect=False, enable_swarming=False):
  if target_bits == 64:
    perf_id = platform
  else:
    perf_id = '%s-%d' % (platform, target_bits)

  SPEC['builders'][name] = BuildSpec(
      'chromium_perf', perf_id, platform, target_bits, enable_swarming)
  assert target_bits not in builders[platform]
  builders[platform][target_bits] = name
  if add_to_bisect:
    SPEC['settings']['bisect_builders'].append(name)


def _AddTestSpec(name, perf_id, platform, target_bits=64,
                 num_host_shards=1, num_device_shards=1):
  for shard_index in xrange(num_host_shards):
    builder_name = '%s (%d)' % (name, shard_index + 1)
    tests = [steps.DynamicPerfTests(
        perf_id, platform, target_bits, num_device_shards=num_device_shards,
        num_host_shards=num_host_shards, shard_index=shard_index)]
    SPEC['builders'][builder_name] = TestSpec(
        'chromium_perf', perf_id, platform, target_bits, tests=tests)


_AddBuildSpec('Android Builder', 'android', target_bits=32)
_AddBuildSpec('Android arm64 Builder', 'android')
_AddBuildSpec('Win Builder', 'win', target_bits=32)
_AddBuildSpec( \
  'Win x64 Builder', 'win', add_to_bisect=True, enable_swarming=True)
_AddBuildSpec('Mac Builder', 'mac', add_to_bisect=True)
_AddBuildSpec('Linux Builder', 'linux', add_to_bisect=True)


_AddTestSpec('Android Galaxy S5 Perf', 'android-galaxy-s5', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3)
_AddTestSpec('Android Nexus5 Perf', 'android-nexus5', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3)
_AddTestSpec('Android Nexus5X Perf', 'android-nexus5X', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3)
_AddTestSpec('Android Nexus6 Perf', 'android-nexus6', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3)
_AddTestSpec('Android Nexus7v2 Perf', 'android-nexus7v2', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3)
_AddTestSpec('Android Nexus9 Perf', 'android-nexus9', 'android',
             num_device_shards=7, num_host_shards=3)
_AddTestSpec('Android One Perf', 'android-one', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3)


_AddTestSpec('Win Zenbook Perf', 'win-zenbook', 'win',
             num_host_shards=5)
_AddTestSpec('Win 10 High-DPI Perf', 'win-high-dpi', 'win',
             num_host_shards=5)
_AddTestSpec('Win 10 Perf', 'chromium-rel-win10', 'win',
             num_host_shards=5)
_AddTestSpec('Win 8 Perf', 'chromium-rel-win8-dual', 'win',
             num_host_shards=5)
_AddTestSpec('Win 7 Perf', 'chromium-rel-win7-dual', 'win',
             target_bits=32, num_host_shards=5)
_AddTestSpec('Win 7 x64 Perf', 'chromium-rel-win7-x64-dual', 'win',
             num_host_shards=5)
_AddTestSpec('Win 7 ATI GPU Perf', 'chromium-rel-win7-gpu-ati', 'win',
             num_host_shards=5)
_AddTestSpec('Win 7 Intel GPU Perf', 'chromium-rel-win7-gpu-intel', 'win',
             num_host_shards=5)
_AddTestSpec('Win 7 Nvidia GPU Perf', 'chromium-rel-win7-gpu-nvidia', 'win',
             num_host_shards=5)


_AddTestSpec('Mac 10.11 Perf', 'chromium-rel-mac11', 'mac',
             num_host_shards=5)
_AddTestSpec('Mac 10.10 Perf', 'chromium-rel-mac10', 'mac',
             num_host_shards=5)
_AddTestSpec('Mac Retina Perf', 'chromium-rel-mac-retina', 'mac',
             num_host_shards=5)
_AddTestSpec('Mac HDD Perf', 'chromium-rel-mac-hdd', 'mac',
             num_host_shards=5)


_AddTestSpec('Linux Perf', 'linux-release', 'linux',
             num_host_shards=5)

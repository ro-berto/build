# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
from . import chromium_webrtc


_builders = collections.defaultdict(dict)


SPEC = {
  'builders': {},
  'settings': {
    'build_gs_bucket': 'chromium-webrtc',
  },
}


def AddBuildSpec(name, perf_id, platform, target_bits=64,
                 build_config='Release'):
  SPEC['builders'][name] = chromium_webrtc.BuildSpec(
      platform, target_bits, perf_id, build_config,
      gclient_config='chromium_webrtc_tot')
  assert target_bits not in _builders[platform]
  _builders[platform][target_bits] = name


def AddTestSpec(name, perf_id, platform, target_bits=64,
                build_config='Release', disable_runhooks=False):
  parent_builder = _builders[platform][target_bits]
  SPEC['builders'][name] = chromium_webrtc.TestSpec(
      parent_builder,
      perf_id,
      platform,
      target_bits,
      disable_runhooks,
      build_config,
      gclient_config='chromium_webrtc_tot',
      test_spec_file='chromium.webrtc.fyi.json')


AddBuildSpec('Win Builder', 'chromium-webrtc-trunk-tot-rel-win', 'win',
             target_bits=32)
AddBuildSpec('Mac Builder', 'chromium-webrtc-trunk-tot-rel-mac', 'mac')
AddBuildSpec('Android Builder (dbg)', 'chromium-webrtc-trunk-tot-dbg-android',
             'android', target_bits=32, build_config='Debug')
AddBuildSpec('Android Builder ARM64 (dbg)',
             'chromium-webrtc-trunk-tot-dbg-android-arm64', 'android',
             build_config='Debug')

AddTestSpec('WinXP Tester', 'chromium-webrtc-trunk-tot-rel-winxp', 'win',
            target_bits=32, disable_runhooks=True)
AddTestSpec('Win7 Tester', 'chromium-webrtc-trunk-tot-rel-win7', 'win',
            target_bits=32)
AddTestSpec('Win10 Tester', 'chromium-webrtc-trunk-tot-rel-win10', 'win',
            target_bits=32)
AddTestSpec('Mac Tester', 'chromium-webrtc-rel-mac', 'mac')
AddTestSpec('Android Tests (dbg) (J Nexus4)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus4-j', 'android',
            target_bits=32, build_config='Debug')
AddTestSpec('Android Tests (dbg) (K Nexus5)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus5-k', 'android',
            target_bits=32, build_config='Debug')
AddTestSpec('Android Tests (dbg) (L Nexus5)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus5', 'android',
            target_bits=32, build_config='Debug')
AddTestSpec('Android Tests (dbg) (L Nexus6)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus6', 'android',
            target_bits=32, build_config='Debug')
AddTestSpec('Android Tests (dbg) (L Nexus7.2)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus72', 'android',
            target_bits=32, build_config='Debug')
AddTestSpec('Android Tests (dbg) (L Nexus9)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus9', 'android',
            build_config='Debug')

# There's only one builder+tester in these waterfalls, which doens't fit well
# into the helper functions here. Hack around it for now.
# TODO(kjellander): Split it to builder+tester when crbug.com/538297 is fixed.
AddBuildSpec('Linux', 'chromium-webrtc-trunk-tot-rel-linux', 'linux')
AddTestSpec('Linux', 'chromium-webrtc-trunk-tot-rel-linux', 'linux')

# Manually overwrite builder-specific configs to make this a builder+tester:
spec = SPEC['builders']['Linux']
del spec['parent_buildername']
spec['bot_type'] = 'builder_tester'
# Restore builder-specific stuff that was overwritten in AddTestSpec above.
spec['chromium_apply_config'] = ['dcheck', 'blink_logging_on']
spec['compile_targets'] = ['chromium_builder_webrtc']

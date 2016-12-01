# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
import collections

from . import chromium_linux
from . import chromium_mac
from . import chromium_win
from . import chromium_webrtc


# GN builders are added first. They're setup to be as similar as possible to
# the builders in Chromium, to be able to detect breakages pre-roll.
SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-webrtc',
  },
  'builders': {},
}


# Remaining builders are WebRTC-specific builders that compile and run tests
# that are focused on testing WebRTC functionality. Some of these tests are
# marked MANUAL since they require audio and/or video devices on the machine
# they run at.
_builders = collections.defaultdict(dict)

def AddBuildSpec(name, platform, target_bits=64, build_config='Release'):
  spec = chromium_webrtc.BuildSpec(
      platform, target_bits, build_config=build_config,
      gclient_config='chromium_webrtc_tot')
  _ConfigureSyncingWebRTCToT(spec)
  SPEC['builders'][name] = spec

  assert target_bits not in _builders[platform]
  _builders[platform][target_bits] = name


def AddTestSpec(name, perf_id, platform, target_bits=64,
                build_config='Release'):
  parent_builder = _builders[platform][target_bits]
  spec = chromium_webrtc.TestSpec(
      parent_builder,
      perf_id,
      platform,
      target_bits,
      build_config,
      gclient_config='chromium_webrtc_tot',
      test_spec_file='chromium.webrtc.fyi.json')
  _ConfigureSyncingWebRTCToT(spec)
  SPEC['builders'][name] = spec


def _ConfigureSyncingWebRTCToT(spec):
  spec['set_component_rev'] = {
    'name': 'src/third_party/webrtc',
    'rev_str': '%s',
  }


AddBuildSpec('Win Builder', 'win', target_bits=32)
AddBuildSpec('Mac Builder', 'mac')
AddBuildSpec('Linux Builder', 'linux')
AddBuildSpec('Android Builder (dbg)', 'android', target_bits=32,
             build_config='Debug')
AddBuildSpec('Android Builder ARM64 (dbg)', 'android', build_config='Debug')

AddTestSpec('Win7 Tester', 'chromium-webrtc-trunk-tot-rel-win7', 'win',
            target_bits=32)
AddTestSpec('Win10 Tester', 'chromium-webrtc-trunk-tot-rel-win10', 'win',
            target_bits=32)
AddTestSpec('Mac Tester', 'chromium-webrtc-trunk-tot-rel-mac', 'mac')
AddTestSpec('Linux Tester', 'chromium-webrtc-trunk-tot-rel-linux', 'linux')
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

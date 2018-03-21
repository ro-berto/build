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

# The bots in chromium.webrtc.fyi are synced to both Chromium ToT and WebRTC
# ToT, where the former is stored as got_cr_revision and the latter is passed as
# got_revision. By setting the Chromium revision to variables that are supported
# by the Perf dashboard, we can still get correct blame lists for the Chrome
# changes.
PERF_CONFIG_MAPPINGS = {
  'r_chromium': 'got_cr_revision',
  'r_chromium_commit_pos': 'got_cr_revision_cp',
}

# Remaining builders are WebRTC-specific builders that compile and run tests
# that are focused on testing WebRTC functionality. Some of these tests are
# marked MANUAL since they require audio and/or video devices on the machine
# they run at.
_builders = collections.defaultdict(dict)

def AddBuildSpec(name, platform, target_bits=64, build_config='Release',
                 bot_type='builder'):
  spec = chromium_webrtc.BuildSpec(
      platform, target_bits, build_config=build_config,
      gclient_config='chromium_webrtc_tot')
  _ConfigureSyncingWebRTCToT(spec)
  spec['bot_type'] = bot_type

  SPEC['builders'][name] = spec
  _builders['%s_%s' % (platform, build_config)][target_bits] = name


def AddTestSpec(name, perf_id, platform, target_bits=64,
                build_config='Release', swarming=None):
  parent_builder = _builders['%s_%s' % (platform, build_config)][target_bits]
  spec = chromium_webrtc.TestSpec(
      parent_builder,
      perf_id,
      platform,
      target_bits,
      build_config,
      perf_config_mappings=PERF_CONFIG_MAPPINGS,
      commit_position_property='got_cr_revision_cp',
      gclient_config='chromium_webrtc_tot',
      test_spec_file='chromium.webrtc.fyi.json',
      enable_baremetal_tests=False,
      swarming=swarming)
  _ConfigureSyncingWebRTCToT(spec)
  SPEC['builders'][name] = spec


def _ConfigureSyncingWebRTCToT(spec):
  spec['set_component_rev'] = {
    'name': 'src/third_party/webrtc',
    'rev_str': '%s',
  }
  spec['extra_got_revision_properties'] = [
    ('src', 'parent_got_cr_revision'),
  ]


AddBuildSpec('Win Builder', 'win', target_bits=32)
AddBuildSpec('Win Builder (dbg)', 'win', target_bits=32, build_config='Debug')
AddBuildSpec('Mac Builder', 'mac')
AddBuildSpec('Mac Builder (dbg)', 'mac', build_config='Debug')
AddBuildSpec('Linux Builder', 'linux')
AddBuildSpec('Linux Builder (dbg)', 'linux', build_config='Debug')

# The Release bot is actually only a builder (not builder+tester). It's
# configured as builder+tester only to skip the archiving of the full build
# (Release bot builds 'all' while Debug builds only the necessary test APK).
# That's the only easy way to avoid archiving the full debug build (13 GB).
AddBuildSpec('Android Builder', 'android', target_bits=32,
             bot_type='builder_tester')
AddBuildSpec('Android Builder (dbg)', 'android', target_bits=32,
             build_config='Debug')
AddBuildSpec('Android Builder ARM64 (dbg)', 'android', build_config='Debug')

AddTestSpec('Win7 Tester', 'chromium-webrtc-trunk-tot-rel-win7', 'win',
            target_bits=32,
            swarming={
              'os': 'Windows-7-SP1',
              'cpu': 'x86-64',
            })
AddTestSpec('Win8 Tester', 'chromium-webrtc-trunk-tot-rel-win8', 'win',
            target_bits=32,
            swarming={
              'os': 'Windows-8.1-SP0',
              'cpu': 'x86-64',
            })
AddTestSpec('Win10 Tester', 'chromium-webrtc-trunk-tot-rel-win10', 'win',
            target_bits=32,
            swarming={
              'os': 'Windows-10',
              'cpu': 'x86-64',
            })
AddTestSpec('Mac Tester', 'chromium-webrtc-trunk-tot-rel-mac', 'mac',
            swarming={
              'os': 'Mac-10.12',
              'cpu': 'x86-64',
            })
AddTestSpec('Linux Tester', 'chromium-webrtc-trunk-tot-rel-linux', 'linux',
            swarming={
              'os': 'Ubuntu-14.04',
              'cpu': 'x86-64',
            })
AddTestSpec('Android Tests (dbg) (K Nexus5)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus5-k', 'android',
            target_bits=32, build_config='Debug',
            swarming={
              'device_type': 'hammerhead',
              'device_os': 'K',
              'os': 'Android',
            })
AddTestSpec('Android Tests (dbg) (L Nexus5)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus5', 'android',
            target_bits=32, build_config='Debug',
            swarming={
              'device_type': 'hammerhead',
              'device_os': 'L',
              'os': 'Android',
            })
AddTestSpec('Android Tests (dbg) (L Nexus6)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus6', 'android',
            target_bits=32, build_config='Debug')
AddTestSpec('Android Tests (dbg) (L Nexus7.2)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus72', 'android',
            target_bits=32, build_config='Debug',
            swarming={
              'device_type': 'flo',
              'device_os': 'L',
              'os': 'Android',
            })
AddTestSpec('Android Tests (dbg) (L Nexus9)',
            'chromium-webrtc-trunk-tot-dbg-android-nexus9', 'android',
            build_config='Debug')

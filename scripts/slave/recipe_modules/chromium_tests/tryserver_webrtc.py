# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_webrtc
from . import steps


SPEC = {
  'settings': {
    'luci_project': 'webrtc',
  },
  'builders': {},
}


def AddBuildSpec(name, platform):
  spec = chromium_webrtc.BuildSpec(
      platform, target_bits=64, build_config='Release',
      gclient_config='chromium')
  SPEC['builders'][name] = spec


AddBuildSpec('android_chromium_compile', 'android')
AddBuildSpec('mac_chromium_compile', 'mac')
AddBuildSpec('linux_chromium_compile', 'linux')
AddBuildSpec('win_chromium_compile', 'win')

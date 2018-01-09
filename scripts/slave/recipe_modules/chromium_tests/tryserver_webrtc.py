# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_webrtc
from . import steps


SPEC = {
  'builders': {},
}


def AddBuildSpec(name, platform):
  spec = chromium_webrtc.BuildSpec(
      platform, target_bits=64, build_config='Release',
      gclient_config='Chromium')
  SPEC['builders'][name] = spec


AddBuildSpec('android_webrtc_compile_rel', 'android')
AddBuildSpec('mac_chromium_webrtc_compile_rel_ng', 'mac')
AddBuildSpec('linux_chromium_webrtc_compile_rel_ng', 'linux')
AddBuildSpec('win_chromium_webrtc_compile_rel_ng', 'win')

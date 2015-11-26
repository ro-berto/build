# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy

from . import chromium_linux
from . import chromium_mac
from . import chromium_win

SPEC = {
  'settings': {},
  'builders': {},
}

def AddBuilder(spec, name):
  SPEC['builders'][name] = copy.deepcopy(spec['builders'][name])

AddBuilder(chromium_linux.SPEC, 'Android GN')
AddBuilder(chromium_linux.SPEC, 'Android GN (dbg)')
AddBuilder(chromium_mac.SPEC, 'Mac GN')
AddBuilder(chromium_mac.SPEC, 'Mac GN (dbg)')
AddBuilder(chromium_win.SPEC, 'Win x64 GN')
AddBuilder(chromium_win.SPEC, 'Win x64 GN (dbg)')

for b in SPEC['builders'].itervalues():
  b.setdefault('gclient_apply_config', [])
  b['gclient_apply_config'].append('chromium_webrtc_tot')
  b['tests'] = []  # These WebRTC builders only run compile.

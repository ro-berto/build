# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.depot_tools.gclient import CONFIG_CTX
from RECIPE_MODULES.depot_tools.gclient.config import ChromiumGitURL


def WebRTCGitURL(_c, *pieces):
  return '/'.join(('https://webrtc.googlesource.com',) + pieces)

@CONFIG_CTX(includes=['_webrtc'])
def webrtc(_):
  pass

@CONFIG_CTX(includes=['webrtc'])
def webrtc_ios(c):
  # WebRTC for iOS depends on the src/third_party/openmax_dl in Chromium, which
  # is set to None for iOS. Because of this, sync Mac as well to get it.
  c.target_os.add('mac')
  c.target_os.add('ios')


@CONFIG_CTX(includes=['webrtc'])
def webrtc_linux_mac_crosscompile_arm64(c):
  # Compiling webrtc on Linux for mac requires fetching mac dependencies.
  c.target_os.add('mac')
  c.target_cpu.add('arm64')


@CONFIG_CTX(includes=['webrtc'])
def webrtc_valgrind(c):
  """Add Valgrind binaries to the gclient solution."""
  c.solutions[0].custom_deps['src/third_party/valgrind'] = \
      ChromiumGitURL(c, 'chromium', 'deps', 'valgrind', 'binaries')

@CONFIG_CTX()
def _webrtc(c):
  """Add the main solution for WebRTC standalone builds.

  This needs to be in it's own configuration that is added first in the
  dependency chain. Otherwise the webrtc-limited solution will end up as the
  first solution in the gclient spec, which doesn't work.
  """
  s = c.solutions.add()
  s.name = 'src'
  s.url = WebRTCGitURL(c, 'src')
  s.deps_file = 'DEPS'
  c.got_revision_mapping['src'] = 'got_revision'

# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import DEPS
CONFIG_CTX = DEPS['gclient'].CONFIG_CTX
ChromeInternalGitURL = DEPS['gclient'].config.ChromeInternalGitURL
ChromiumGitURL = DEPS['gclient'].config.ChromiumGitURL

def WebRTCGitURL(_c, *pieces):
  return '/'.join(('https://webrtc.googlesource.com',) + pieces)

@CONFIG_CTX(includes=['_webrtc'])
def webrtc(c):
  pass

@CONFIG_CTX(includes=['_webrtc', '_webrtc_limited'])
def webrtc_with_limited(c):
  # This is only used by Win7 bots that are builder+tester and not just testers.
  # It's used to get DirectX, which is built into the Win8 SDK but not Win7.
  # Remove this when we no longer have Win7 builder+testers.
  pass

@CONFIG_CTX(includes=['webrtc'])
def webrtc_ios(c):
  # WebRTC for iOS depends on the src/third_party/openmax_dl in Chromium, which
  # is set to None for iOS. Because of this, sync Mac as well to get it.
  c.target_os.add('mac')
  c.target_os.add('ios')

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

@CONFIG_CTX()
def _webrtc_limited(c):
  """Helper config for loading the webrtc-limited solution.

  The webrtc-limited solution contains non-redistributable code.
  """
  s = c.solutions.add()
  s.name = 'webrtc-limited'
  s.url = ChromeInternalGitURL(c, 'chrome', 'deps', 'webrtc-limited')
  s.deps_file = 'DEPS'

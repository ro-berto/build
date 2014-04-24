# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.gclient import CONFIG_CTX
from slave.recipe_modules.gclient.config import ChromeSvnSubURL,\
  ChromiumSvnSubURL


@CONFIG_CTX(includes=['_webrtc', '_webrtc_limited'])
def webrtc(c):
  pass

@CONFIG_CTX(includes=['webrtc'])
def webrtc_asan(c):
  pass


@CONFIG_CTX(includes=['webrtc'])
def webrtc_android(c):
  c.target_os = ['android']


@CONFIG_CTX(includes=['webrtc_android'])
def webrtc_android_clang(c):
  pass


@CONFIG_CTX(includes=['chromium', '_webrtc_limited'])
def webrtc_android_apk(c):
  c.target_os = ['android']

  # The webrtc.DEPS solution pulls in additional resources needed for running
  # WebRTC-specific test setups in Chrome.
  s = c.solutions.add()
  s.name = 'webrtc.DEPS'
  s.url = ChromiumSvnSubURL(c, 'chrome', 'trunk', 'deps', 'third_party',
                            'webrtc', 'webrtc.DEPS')

  # Have the WebRTC revision appear in the web UI instead of Chromium's.
  del c.got_revision_mapping['src']
  c.got_revision_mapping['src/third_party/webrtc'] = 'got_revision'


@CONFIG_CTX()
def _webrtc(c):
  """Add the main solution for WebRTC standalone builds.

  This needs to be in it's own configuration that is added first in the
  dependency chain. Otherwise the webrtc-limited solution will end up as the
  first solution in the gclient spec, which doesn't work.
  """
  s = c.solutions.add()
  s.name = 'src'
  s.url = WebRTCSvnURL(c, 'trunk')
  s.custom_vars['root_dir'] = 'src'
  c.got_revision_mapping['webrtc'] = 'got_revision'


@CONFIG_CTX()
def _webrtc_limited(c):
  """Helper config for loading the webrtc-limited solution.

  The webrtc-limited solution contains non-redistributable code.
  """
  s = c.solutions.add()
  s.name = 'webrtc-limited'
  s.url = ChromeSvnSubURL(c, 'chrome-internal', 'trunk', 'webrtc-limited')
  s.custom_vars['root_dir'] = 'src'


def WebRTCSvnURL(c, *pieces):
  BASES = ('http://webrtc.googlecode.com/svn',
           'svn://svn-mirror.golo.chromium.org/webrtc')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)

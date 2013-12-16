# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.gclient import CONFIG_CTX
from slave.recipe_config import BadConf
from slave.recipe_modules.gclient.config import ChromeSvnSubURL,\
  ChromiumSvnSubURL


@CONFIG_CTX(includes=['chromium', '_webrtc_additional_solutions'])
def webrtc_android_apk_try_builder(c):
  c.target_os = ['android']

  # TODO(kjellander): Switch to use the webrtc_revision gyp variable in DEPS
  # as soon we've switched over to use the trunk branch instead of the stable
  # branch (which is about to be retired).
  c.solutions[0].custom_deps['src/third_party/webrtc'] = (
       'http://webrtc.googlecode.com/svn/trunk/webrtc')


@CONFIG_CTX()
def _webrtc_additional_solutions(c):
  """Helper config for loading additional solutions.

  The webrtc-limited solution contains non-redistributable code.
  The webrtc.DEPS solution pulls in additional resources needed for running
  WebRTC-specific test setups.
  """
  if c.GIT_MODE:
    raise BadConf('WebRTC only supports svn')

  s = c.solutions.add()
  s.name = 'webrtc-limited'
  s.url = ChromeSvnSubURL(c, 'chrome-internal', 'trunk', 'webrtc-limited')

  s = c.solutions.add()
  s.name = 'webrtc.DEPS'
  s.url = ChromiumSvnSubURL(c, 'chrome', 'trunk', 'deps', 'third_party',
                            'webrtc', 'webrtc.DEPS')

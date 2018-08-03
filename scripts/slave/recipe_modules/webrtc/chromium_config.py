# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import BadConf
from recipe_engine.config_types import Path

import DEPS
CONFIG_CTX = DEPS['chromium'].CONFIG_CTX


@CONFIG_CTX(includes=['chromium'])
def webrtc_default(c):
  _compiler_defaults(c)

@CONFIG_CTX(includes=['webrtc_default'])
def webrtc_android_perf(c):
  if c.BUILD_CONFIG != 'Release':
    raise BadConf('Perf bots must use Release configs!') # pragma: no cover
  c.compile_py.default_targets = ['low_bandwidth_audio_test',
                                  'webrtc_perf_tests']
                                  # 'AppRTCMobileTestStubbedVideoIO'

@CONFIG_CTX(includes=['webrtc_default'])
def webrtc_desktop_perf(c):
  if c.BUILD_CONFIG != 'Release':
    raise BadConf('Perf bots must use Release configs!') # pragma: no cover
  c.compile_py.default_targets = ['isac_fix_test', 'low_bandwidth_audio_test',
                                  'webrtc_perf_tests']

# TODO(kjellander): Remove as soon there's a way to get the sanitizer bots to
# set swarming tags properly without the chromium recipe module configs (which
# depend on clang)
@CONFIG_CTX(includes=['chromium_clang'])
def webrtc_clang(c):
  _compiler_defaults(c)

def _compiler_defaults(c):
  c.compile_py.default_targets = []

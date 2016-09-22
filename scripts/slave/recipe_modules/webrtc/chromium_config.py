# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import BadConf
from recipe_engine.config_types import Path

import DEPS
CONFIG_CTX = DEPS['chromium'].CONFIG_CTX


SUPPORTED_TARGET_ARCHS = ('intel', 'arm')


@CONFIG_CTX(includes=['chromium', 'dcheck', 'webrtc_openh264'])
def webrtc_standalone(c):
  _compiler_defaults(c)

  c.runtests.memory_tests_runner = c.CHECKOUT_PATH.join(
      'tools', 'valgrind-webrtc', 'webrtc_tests',
      platform_ext={'win': '.bat', 'mac': '.sh', 'linux': '.sh'})

# TOOD(kjellander): Cleanup after migrating client.webrtc.fyi bots to MB.
@CONFIG_CTX(includes=['ninja', 'gcc', 'goma'])
def webrtc_gcc(c):
  _compiler_defaults(c)

# TOOD(kjellander): Cleanup after migrating client.webrtc.fyi bots to MB.
@CONFIG_CTX(includes=['chromium_clang', 'dcheck', 'webrtc_openh264'])
def webrtc_clang(c):
  _compiler_defaults(c)

@CONFIG_CTX()
def webrtc_libfuzzer(c):
  c.gn_args.extend([
    'use_libfuzzer=true',
    'is_asan=true',
  ])

@CONFIG_CTX()
def webrtc_use_src_side_runtest_py(c):
  c.runtest_py.src_side = True

# TODO(kjellander): Cleanup after migrating client.webrtc.fyi bots to MB.
@CONFIG_CTX()
def webrtc_openh264(c):
  if c.TARGET_PLATFORM == 'ios':
    raise BadConf('ffmpeg decode not supported for iOS')  # pragma: no cover
  if c.TARGET_PLATFORM == 'android':
    raise BadConf('h264 decode not supported for Android')  # pragma: no cover
  c.gyp_env.GYP_DEFINES['ffmpeg_branding'] = 'Chrome'
  c.gyp_env.GYP_DEFINES['rtc_use_h264'] = 1
  c.gn_args = [
    'ffmpeg_branding="Chrome"',
    'rtc_use_h264=true',
  ]

def _compiler_defaults(c):
  c.compile_py.default_targets = []

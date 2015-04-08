# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import BadConf

from RECIPE_MODULES.chromium import CONFIG_CTX
from slave.recipe_config_types import Path


SUPPORTED_TARGET_ARCHS = ('intel', 'arm')


@CONFIG_CTX(includes=['chromium'])
def webrtc_standalone(c):
  _compiler_defaults(c)

  c.runtests.memory_tests_runner = Path('[CHECKOUT]', 'tools',
                                        'valgrind-webrtc', 'webrtc_tests',
                                        platform_ext={'win': '.bat',
                                                      'mac': '.sh',
                                                      'linux': '.sh'})

@CONFIG_CTX(includes=['chromium_clang'])
def webrtc_clang(c):
  _compiler_defaults(c)

@CONFIG_CTX(includes=['chromium', '_webrtc_ios'])
def webrtc_ios32(c):
  pass

@CONFIG_CTX(includes=['chromium_no_goma', '_webrtc_ios'])
def webrtc_ios64(c):
  pass

@CONFIG_CTX(includes=['static_library'])
def _webrtc_ios(c):
  if c.HOST_PLATFORM != 'mac':
    raise BadConf('Only "mac" host platform is supported for iOS (got: "%s")' %
                  c.HOST_PLATFORM)  # pragma: no cover
  if c.TARGET_PLATFORM != 'ios':
    raise BadConf('Only "ios" target platform is supported (got: "%s")' %
                  c.TARGET_PLATFORM)  # pragma: no cover
  c.build_config_fs = c.BUILD_CONFIG + '-iphoneos'

  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['build_with_libjingle'] = 1
  gyp_defs['chromium_ios_signing'] = 0
  gyp_defs['key_id'] = ''
  gyp_defs['OS'] = c.TARGET_PLATFORM
  _compiler_defaults(c)

@CONFIG_CTX(includes=['gn'])
def webrtc_gn(c):
  c.compile_py.default_targets = ['all']
  c.project_generator.args = ['build_with_chromium=false']

def _compiler_defaults(c):
  c.compile_py.default_targets = ['All']
  if c.TARGET_PLATFORM in ('mac', 'ios'):
    c.gyp_env.GYP_DEFINES['mac_sdk'] = '10.9'

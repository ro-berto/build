# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import BadConf

from RECIPE_MODULES.chromium import CONFIG_CTX


SUPPORTED_TARGET_ARCHS = ('intel', 'arm')


@CONFIG_CTX(includes=['ninja'])
def webrtc_standalone(c):
  c.compile_py.default_targets = ['All']


@CONFIG_CTX(includes=['android'])
def webrtc_android_apk_try_builder(c):
  if c.TARGET_PLATFORM != 'android':
    raise BadConf('Only "android" platform is supported (got: "%s")' %
                  c.TARGET_PLATFORM)
  if c.TARGET_ARCH not in SUPPORTED_TARGET_ARCHS:
    raise BadConf('Only "%s" architectures are supported (got: "%s")' %
                  (','.join(SUPPORTED_TARGET_ARCHS), c.TARGET_ARCH))

  c.compile_py.default_targets = ['android_builder_webrtc']
  c.gyp_env.GYP_GENERATOR_FLAGS['default_target'] = 'android_builder_webrtc'
  c.gyp_env.GYP_DEFINES['include_tests'] = 1


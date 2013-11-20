# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config_types import Path
from slave import recipe_config
from RECIPE_MODULES.chromium import CONFIG_CTX


@CONFIG_CTX()
def v8(c):
  targ_arch = c.gyp_env.GYP_DEFINES.get('target_arch')
  if not targ_arch:  # pragma: no cover
    raise recipe_config.BadConf('v8 must have a valid target_arch.')
  c.gyp_env.GYP_DEFINES['v8_target_arch'] = targ_arch
  del c.gyp_env.GYP_DEFINES['component']
  c.build_config_fs = c.BUILD_CONFIG
  c.build_dir = Path('[CHECKOUT]')

  c.compile_py.build_tool = 'make'
  c.compile_py.default_targets = ['buildbot']
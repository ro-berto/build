# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.chromium import CONFIG_CTX
from slave.recipe_config_types import Path


SYZYGY_SLN = Path('[CHECKOUT]', 'syzygy', 'syzygy.sln')
ALL_SLN = Path('[CHECKOUT]', 'syzygy', 'build', 'all.sln')


@CONFIG_CTX(includes=['msvs', 'msvs2013'])
def _syzygy_base(c):
  c.project_generator.tool = 'gyp'

  # We don't use a component build, so remove the GYP define.
  c.gyp_env.GYP_DEFINES.pop('component', None)


@CONFIG_CTX(includes=['_syzygy_base'])
def syzygy(c):
  assert 'official_build' not in c.gyp_env.GYP_DEFINES
  c.compile_py.default_targets.clear()
  c.compile_py.default_targets.add('build_all')
  c.compile_py.solution = SYZYGY_SLN


@CONFIG_CTX(includes=['_syzygy_base'],
            config_vars={'BUILD_CONFIG': 'Release'})
def syzygy_official(c):
  c.compile_py.clobber = True
  c.compile_py.default_targets.clear()
  c.compile_py.default_targets.add('official_build')
  c.compile_py.solution = ALL_SLN
  c.gyp_env.GYP_DEFINES['official_build'] = 1

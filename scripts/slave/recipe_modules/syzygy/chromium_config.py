# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import DEPS
CONFIG_CTX = DEPS['chromium'].CONFIG_CTX

from recipe_engine.config_types import Path


@CONFIG_CTX(includes=['ninja'])
def _syzygy(c):
  c.project_generator.tool = 'gyp'

  # We don't use a component build, so remove the GYP define.
  c.gyp_env.GYP_DEFINES.pop('component', None)

  # Generate MSVS projects as well for ease of debugging on the bot.
  c.gyp_env.GYP_GENERATORS.add('ninja')
  c.gyp_env.GYP_GENERATORS.add('msvs-ninja')
  # Inject a Ninja no-op build confirmation step.
  c.compile_py.ninja_confirm_noop = True


# Configuration to be used by continuous builders: Debug, Release and Coverage.
@CONFIG_CTX(includes=['_syzygy'])
def syzygy(c):
  assert 'official_build' not in c.gyp_env.GYP_DEFINES
  c.compile_py.default_targets.clear()
  c.compile_py.default_targets.add('build_all')


@CONFIG_CTX(includes=['_syzygy'],
            config_vars={'TARGET_BITS': 64,
                         'HOST_BITS': 64})
def syzygy_x64(c):
  assert 'official_build' not in c.gyp_env.GYP_DEFINES
  c.compile_py.default_targets.clear()
  c.compile_py.default_targets.add('build_all')


@CONFIG_CTX(includes=['_syzygy', 'clobber'],
            config_vars={'BUILD_CONFIG': 'Release'})
def syzygy_official(c):
  c.compile_py.default_targets.clear()
  c.compile_py.default_targets.add('official_build')
  c.gyp_env.GYP_DEFINES['official_build'] = 1


@CONFIG_CTX(includes=['_syzygy', 'clobber'],
            config_vars={'BUILD_CONFIG': 'Release'})
def kasko_official(c):
  c.compile_py.default_targets.clear()
  c.compile_py.default_targets.add('official_kasko_build')
  c.gyp_env.GYP_DEFINES['official_build'] = 1

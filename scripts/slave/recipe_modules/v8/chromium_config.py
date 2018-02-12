# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import BadConf
from recipe_engine.config_types import Path
from recipe_engine import config as recipe_config

import DEPS
CONFIG_CTX = DEPS['chromium'].CONFIG_CTX


@CONFIG_CTX()
def v8(c):
  # TODO(machenbach): Remove 'gyp' related logic.
  # project_generator.tool has been set default as 'mb' everywhere else.
  c.project_generator.tool = 'gyp'
  targ_arch = c.gyp_env.GYP_DEFINES.get('target_arch')
  if not targ_arch:  # pragma: no cover
    raise recipe_config.BadConf('v8 must have a valid target_arch.')
  c.gyp_env.GYP_DEFINES['v8_target_arch'] = targ_arch
  if c.TARGET_PLATFORM == 'android':
    c.gyp_env.GYP_DEFINES['OS'] = 'android'
  del c.gyp_env.GYP_DEFINES['component']
  c.build_dir = c.CHECKOUT_PATH.join('out')

  if c.BUILD_CONFIG == 'Debug':
    c.gyp_env.GYP_DEFINES['v8_optimized_debug'] = 1
    c.gyp_env.GYP_DEFINES['v8_enable_slow_dchecks'] = 1

  # Chromium adds '_x64' to the output folder, which is only understood when
  # compiling v8 standalone with ninja.
  if c.HOST_PLATFORM == 'win' and c.TARGET_BITS == 64:
    c.build_config_fs = c.BUILD_CONFIG


@CONFIG_CTX(includes=['v8'])
def arm_hard_float(c):
  c.gn_args.append('arm_float_abi="hard"')


@CONFIG_CTX(includes=['v8'])
def default_target_v8_clusterfuzz(c):
  c.compile_py.default_targets = ['v8_clusterfuzz']


@CONFIG_CTX(includes=['v8'])
def default_target_v8_archive(c):
  c.compile_py.default_targets = ['v8_archive']


# TODO(machenbach): Set up gclient variable for this.
@CONFIG_CTX(includes=['v8'])
def gcmole(c):
  c.gyp_env.GYP_DEFINES['gcmole'] = 1


# TODO(machenbach): Set up gclient variable for this.
@CONFIG_CTX(includes=['v8'])
def jsfunfuzz(c):
  c.gyp_env.GYP_DEFINES['jsfunfuzz'] = 1


@CONFIG_CTX(includes=['ninja'])
def v8_ninja(c):
  if c.HOST_PLATFORM == 'win' and c.TARGET_BITS == 64:
    # Windows requires 64-bit builds to be in <dir>_x64 with ninja. See
    # crbug.com/470681.
    c.build_config_fs = c.BUILD_CONFIG + '_x64'


# Work-around for obtaining the right build dir on linux slave that trigger
# windows 64 bit swarming jobs.
@CONFIG_CTX(includes=['v8'])
def use_windows_swarming_slaves(c):
  if c.TARGET_BITS == 64:
    c.build_config_fs = c.BUILD_CONFIG + '_x64'


@CONFIG_CTX(includes=['v8'])
def v8_android(c):
  c.gn_args.append('symbol_level=1')
  c.gn_args.append('v8_android_log_stdout=true')


@CONFIG_CTX(includes=['v8'])
def v8_static_library(c):
  c.gn_args.append('v8_static_library=true')

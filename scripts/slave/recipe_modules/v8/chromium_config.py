# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config import BadConf
from recipe_engine.config_types import Path
from recipe_engine import config as recipe_config

import DEPS
CONFIG_CTX = DEPS['chromium'].CONFIG_CTX


@CONFIG_CTX(includes=['ninja'])
def v8(c):
  c.project_generator.tool = 'mb'
  c.build_dir = c.CHECKOUT_PATH.join('out')

  if c.HOST_PLATFORM == 'win' and c.TARGET_BITS == 64:
    # TODO(machenbach): This resets Chromium's defauls, which add a _x64 suffix.
    # We sould remove it when crbug.com/470681 is resolved.
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


@CONFIG_CTX(includes=['v8'])
def v8_android(c):
  c.gn_args.append('symbol_level=1')
  c.gn_args.append('v8_android_log_stdout=true')


@CONFIG_CTX(includes=['v8'])
def v8_static_library(c):
  c.gn_args.append('v8_static_library=true')

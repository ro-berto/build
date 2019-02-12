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

  if c.HOST_PLATFORM == 'mac':
    # There are several ways to download hermetic XCode:
    #  - via recipe logic in api.chromium.runhooks and mac_toolchains DEPS hook
    #  - via api.chromium.ensure_toolchains method
    #  - via osx_sdk recipe module
    #
    # The first mechanism is deprecated and is being phased out, the second
    # mechanism does not work on LUCI yet. The setting below disables the recipe
    # logic for the DEPS hook, thus preventing the XCode being fetched by the
    # chromium module as it thinks that we use api.chromium.ensure_toolchains,
    # but in practice we do not call it and use osx_sdk module instead.
    c.mac_toolchain.enabled = True


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


@CONFIG_CTX(includes=['v8'])
def slow_dchecks(c):
  c.gn_args.append('v8_enable_slow_dchecks=true')


@CONFIG_CTX(includes=['ninja', 'gn', 'clang', 'goma'])
def node_ci(c):
  c.use_gyp_env = False
  c.gn_args.append('use_sysroot=true')
  c.gn_args.append('use_custom_libcxx=true')

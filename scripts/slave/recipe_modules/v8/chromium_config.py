# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium import CONFIG_CTX


@CONFIG_CTX(includes=['ninja'])
def v8(c):
  c.project_generator.tool = 'mb'
  c.build_dir = c.CHECKOUT_PATH.join('out')

  if c.HOST_PLATFORM == 'win' and c.TARGET_BITS == 64:
    # TODO(machenbach): This resets Chromium's defauls, which add a _x64 suffix.
    # We sould remove it when crbug.com/470681 is resolved.
    c.build_config_fs = c.BUILD_CONFIG

  if c.HOST_PLATFORM == 'mac' and c.TARGET_PLATFORM != 'ios':
    # Update via recipe logic in api.chromium.runhooks and mac_toolchains DEPS
    # hook.
    c.mac_toolchain.enabled = False

  if c.TARGET_PLATFORM == 'mac':
    c.env.FORCE_MAC_TOOLCHAIN = 1


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
  if c.HOST_PLATFORM != 'win':
    c.gn_args.append('use_sysroot=true')
    c.gn_args.append('use_custom_libcxx=true')

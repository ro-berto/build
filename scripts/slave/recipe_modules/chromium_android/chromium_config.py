# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config_types import Path
from slave import recipe_config

from RECIPE_MODULES.chromium import CONFIG_CTX

@CONFIG_CTX(includes=['ninja', 'static_library'],
            config_vars={'TARGET_ARCH': 'arm', 'TARGET_BITS': 32})
def android_defaults(c):
  c.compile_py.default_targets=[]
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['fastbuild'] = 1
  gyp_defs['OS'] = 'android'
  gyp_defs['host_os'] = 'linux'

  if c.HOST_PLATFORM != 'linux':
    raise recipe_config.BadConf('Can only build android on linux.')
  if c.TARGET_BITS != 32:
    raise recipe_config.BadConf('Android cannot target %d bits' % c.TARGET_BITS)


@CONFIG_CTX(includes=['android_defaults', 'default_compiler', 'goma'])
def main_builder(c):
  if c.TARGET_ARCH != 'arm':
    raise recipe_config.BadConf(
      'Cannot target arm with TARGET_ARCH == %s' % c.TARGET_ARCH)

@CONFIG_CTX(includes=['android_defaults', 'clang', 'goma'])
def clang_builder(c):
  pass

@CONFIG_CTX(includes=['main_builder'])
def component_builder(c):
  c.gyp_env.GYP_DEFINES['component'] = 'shared_library'

@CONFIG_CTX(includes=['android_defaults', 'default_compiler', 'goma'],
            config_vars={'TARGET_ARCH': 'intel'})
def x86_builder(c):
  if c.TARGET_ARCH != 'intel':
    raise recipe_config.BadConf(
      'Cannot target x86 with TARGET_ARCH == %s' % c.TARGET_ARCH)

@CONFIG_CTX(includes=['android_defaults', 'default_compiler'],
            config_vars={'TARGET_ARCH': 'mips'})
def mips_builder(c):
  if c.TARGET_ARCH != 'mips':
    raise recipe_config.BadConf('I dunno what to put in a mips builder!')

@CONFIG_CTX(includes=['main_builder'])
def dartium_builder(c):
  c.compile_py.default_targets=['chrome_apk', 'content_shell_apk']

@CONFIG_CTX(includes=['main_builder'])
def klp_builder(c):
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['android_sdk_build_tools_version'] = 'android-4.4'
  gyp_defs['android_sdk_version'] = '4.4'
  gyp_defs['android_sdk_root'] = Path(
    '[CHECKOUT]', 'third_party', 'android_tools_internal', 'sdk')

@CONFIG_CTX(includes=['main_builder'])
def try_builder(c):
  pass

@CONFIG_CTX(includes=['x86_builder'])
def x86_try_builder(c):
  pass

@CONFIG_CTX(includes=['android_defaults'])
def tests_base(c):
  pass

@CONFIG_CTX(includes=['tests_base'])
def main_tests(c):
  pass

@CONFIG_CTX(includes=['tests_base'])
def clang_tests(c):
  pass

@CONFIG_CTX(includes=['tests_base'])
def enormous_tests(c):
  pass

@CONFIG_CTX(includes=['tests_base'])
def try_instrumentation_tests(c):
  pass

@CONFIG_CTX(includes=['x86_builder'])
def x86_try_instrumentation_tests(c):
  pass

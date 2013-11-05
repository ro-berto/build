# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config_types import Path

from RECIPE_MODULES.chromium import CONFIG_CTX

@CONFIG_CTX(includes=['ninja', 'static_library'])
def android_defaults(c):
  c.compile_py.default_targets=['All']
  c.gyp_env.GYP_CROSSCOMPILE = 1
  c.gyp_env.GYP_GENERATORS.add('ninja')
  c.gyp_env.GYP_GENERATOR_FLAGS['default_target'] = 'All'
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['fastbuild'] = 1
  gyp_defs['OS'] = 'android'
  gyp_defs['host_os'] = 'linux'
  gyp_defs['gcc_version'] = 46
  gyp_defs['order_text_section'] = Path(
    '[CHECKOUT]', 'orderfiles', 'orderfile.out')
  gyp_defs['target_arch'] = 'arm'


@CONFIG_CTX(includes=['android_defaults', 'default_compiler', 'goma'])
def main_builder(c):
  pass

@CONFIG_CTX(includes=['android_defaults', 'clang', 'goma'])
def clang_builder(c):
  pass

@CONFIG_CTX(includes=['main_builder'])
def component_builder(c):
  c.gyp_env.GYP_DEFINES['component'] = 'shared_library'

@CONFIG_CTX(includes=['main_builder'])
def x86_builder(c):
  c.gyp_env.GYP_DEFINES['target_arch'] = 'ia32'

@CONFIG_CTX(includes=['x86_builder'])
def dartium_builder(c):
  c.compile_py.default_targets=['chrome_apk', 'content_shell_apk']

@CONFIG_CTX(includes=['main_builder'])
def klp_builder(c):
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['android_sdk_version'] = '4.4'
  gyp_defs['android_sdk_root'] = Path(
    '[CHECKOUT]', 'third_party', 'android_tools_internal', 'sdk')

@CONFIG_CTX(includes=['main_builder'])
def try_builder(c):
  pass

@CONFIG_CTX(includes=['x86_builder', 'try_builder'])
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

@CONFIG_CTX(includes=['tests_base'])
def x86_try_instrumentation_tests(c):
  pass

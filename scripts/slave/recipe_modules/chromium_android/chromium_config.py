# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.chromium import CONFIG_CTX

@CONFIG_CTX(includes=['ninja'])
def android_defaults(c):
  c.compile_py.default_targets=['All']
  c.gyp_env.GYP_DEFINES['fastbuild'] = 1

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
  pass

@CONFIG_CTX(includes=['main_builder'])
def klp_builder(c):
  pass

@CONFIG_CTX(includes=['main_builder'])
def try_builder(c):
  pass

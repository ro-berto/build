# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Dict, Single, Static
from slave.recipe_config_types import Path

def BaseConfig(INTERNAL, REPO_NAME, REPO_URL, **_kwargs):
  return ConfigGroup(
    INTERNAL = Static(INTERNAL),
    REPO_NAME = Static(REPO_NAME),
    REPO_URL = Static(REPO_URL),
    target_arch = Single(basestring, required=False, empty_val=''),
    extra_env = Dict(value_type=(basestring,int,Path)),
    run_findbugs = Single(bool, required=False, empty_val=False),
    run_lint = Single(bool, required=False, empty_val=False),
    run_checkdeps = Single(bool, required=False, empty_val=False),
    apply_svn_patch = Single(bool, required=False, empty_val=False),
    build_internal_android = Static(Path('[BUILD_INTERNAL]',
                                         'scripts', 'slave', 'android'))
  )


VAR_TEST_MAP = {
  'INTERNAL': [True, False],
  'REPO_NAME': ['src', 'internal'],
  'REPO_URL': ['bob_dot_org', 'mike_dot_org'],
}

def TEST_NAME_FORMAT(kwargs):
  name = 'repo-%(REPO_NAME)s-from-url-%(REPO_URL)s' % kwargs
  if kwargs['INTERNAL']:
    return name + '-internal'
  else:
    return name

config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_NAME_FORMAT)

@config_ctx(is_root=True)
def main_builder(c):
  pass

@config_ctx()
def clang_builder(c):
  if c.INTERNAL:
    c.run_findbugs = True
    c.run_lint = True
    c.run_checkdeps = True

@config_ctx()
def component_builder(c):
  pass

@config_ctx()
def x86_builder(c):
  c.target_arch = 'x86'

@config_ctx()
def klp_builder(c):
  c.extra_env = {
    'ANDROID_SDK_BUILD_TOOLS_VERSION': 'android-KeyLimePie',
    'ANDROID_SDK_ROOT': Path(
      '[CHECKOUT]', 'third_party', 'android_tools_internal', 'sdk'),
    'ANDROID_SDK_VERSION': 'KeyLimePie'
  }

@config_ctx()
def try_builder(c):
  if c.INTERNAL:
    c.apply_svn_patch = True
    c.run_findbugs = True
    c.run_lint = True

@config_ctx(includes=['x86_builder', 'try_builder'])
def x86_try_builder(c):
  pass

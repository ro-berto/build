# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import ConfigList, Dict, List, Single, Static
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
    run_stack_tool_steps = Single(bool, required=False, empty_val=False),
    asan_symbolize = Single(bool, required=False, empty_val=False),
    extra_deploy_opts = List(inner_type=basestring),
    instrumentation_tests = ConfigList(
      lambda: ConfigGroup(
        annotation = Single(basestring, required=True),
        exclude_annotation = Single(basestring, required=False, empty_val=None)
      )
    ),
    build_internal_android = Static(Path('[BUILD_INTERNAL]',
                                         'scripts', 'slave', 'android')),
    cr_build_android = Static(Path('[CHECKOUT]', 'build', 'android')),
    internal_dir = Single(Path),
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
def base_config(c):
  if c.INTERNAL:
    c.internal_dir = Path('[CHECKOUT]', c.REPO_NAME.split('/', 1)[-1])

@config_ctx()
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
def x86_base(c):
  c.target_arch = 'x86'

@config_ctx(includes=['x86_base'])
def x86_builder(c):
  pass

@config_ctx()
def klp_builder(c):
  c.extra_env = {
    'ANDROID_SDK_BUILD_TOOLS_VERSION': 'android-KeyLimePie',
    'ANDROID_SDK_ROOT': Path(
      '[CHECKOUT]', 'third_party', 'android_tools_internal', 'sdk'),
    'ANDROID_SDK_VERSION': 'KeyLimePie'
  }

@config_ctx()
def try_base(c):
  if c.INTERNAL:
    c.apply_svn_patch = True

@config_ctx(includes=['try_base'])
def try_builder(c):
  if c.INTERNAL:
    c.run_findbugs = True
    c.run_lint = True

@config_ctx(includes=['x86_builder', 'try_builder'])
def x86_try_builder(c):
  pass

@config_ctx()
def tests_base(c):
  c.run_stack_tool_steps = True

@config_ctx(includes=['tests_base'])
def instrumentation_tests(c):
  c.instrumentation_tests.append({'annotation': 'Smoke'})
  c.instrumentation_tests.append({'annotation': 'SmallTest'})
  c.instrumentation_tests.append({'annotation': 'MediumTest'})
  c.instrumentation_tests.append({'annotation': 'LargeTest'})

@config_ctx(includes=['instrumentation_tests'])
def main_tests(c):
  pass

@config_ctx(includes=['tests_base'])
def clang_tests(c):
  c.instrumentation_tests.append({'annotation': 'Smoke'})
  c.asan_symbolize = True

@config_ctx(includes=['tests_base'])
def enormous_tests(c):
  c.extra_deploy_opts = ['--await-internet']
  c.instrumentation_tests.append({'annotation': 'EnormousTest',
                                  'exclude_annotation': 'Feature=Sync'})
  c.instrumentation_tests.append({'annotation': 'Feature=Sync',
                                  'exclude_annotation': 'FlakyTest'})

@config_ctx(includes=['try_base', 'instrumentation_tests'])
def try_instrumentation_tests(c):
  pass

@config_ctx(includes=['x86_base', 'try_base', 'instrumentation_tests'])
def x86_try_instrumentation_tests(c):
  c.extra_deploy_opts.append('--non-rooted')

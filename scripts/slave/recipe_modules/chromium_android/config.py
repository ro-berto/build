# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import ConfigList, Dict, List, Single, Static
from slave.recipe_config_types import Path

def BaseConfig(INTERNAL=False, REPO_NAME=None, REPO_URL=None,
               BUILD_CONFIG='Debug', **_kwargs):
  return ConfigGroup(
    INTERNAL = Static(INTERNAL),
    REPO_NAME = Static(REPO_NAME),
    REPO_URL = Static(REPO_URL),
    BUILD_CONFIG = Static(BUILD_CONFIG),
    revision = Single(basestring),
    extra_env = Dict(value_type=(basestring,int,Path)),
    run_findbugs = Single(bool, required=False, empty_val=False),
    run_lint = Single(bool, required=False, empty_val=False),
    run_checkdeps = Single(bool, required=False, empty_val=False),
    apply_svn_patch = Single(bool, required=False, empty_val=False),
    run_stack_tool_steps = Single(bool, required=False, empty_val=False),
    asan_symbolize = Single(bool, required=False, empty_val=False),
    get_app_manifest_vars = Single(bool, required=False, empty_val=True),
    run_tree_truth = Single(bool, required=False, empty_val=True),
    deps_file = Single(basestring, required=False, empty_val='.DEPS.git'),
    # deps_dir: where to checkout the gclient deps file
    deps_dir = Single(basestring, required=False, empty_val=REPO_NAME),
    managed = Single(bool, required=False, empty_val=True),
    extra_deploy_opts = List(inner_type=basestring),
    tests = List(inner_type=basestring),
    build_internal_android = Static(Path('[BUILD_INTERNAL]',
                                         'scripts', 'slave', 'android')),
    cr_build_android = Static(Path('[CHECKOUT]', 'build', 'android')),
    internal_dir = Single(Path),
    gclient_custom_deps = Dict(value_type=(basestring, types.NoneType)),
    storage_bucket = Single(basestring),
    archive_clusterfuzz = Single(bool, required=False, empty_val=False),
    channel = Single(basestring, empty_val='chrome'),
  )


VAR_TEST_MAP = {
  'INTERNAL': [True, False],
  'REPO_NAME': ['src/clank'],
  'REPO_URL': ['<hidden>'],  # supplied in build properties
  'BUILD_CONFIG': ['Debug', 'Release'],
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
  c.revision = 'refs/remotes/origin/master'

@config_ctx()
def main_builder(c):
  pass

@config_ctx()
def clang_builder(c):
  if c.INTERNAL:
    c.run_findbugs = True
    c.run_lint = True
    c.run_checkdeps = True

@config_ctx(config_vars={'BUILD_CONFIG': 'Release'})
def clang_release_builder(c):
  c.asan_symbolize = True
  c.storage_bucket = 'chrome-test-builds/android'
  c.archive_clusterfuzz = True

@config_ctx()
def component_builder(c):
  pass

@config_ctx()
def x86_base(c):
  pass

@config_ctx(includes=['x86_base'])
def x86_builder(c):
  pass

@config_ctx()
def mipsel_base(c):
  pass

@config_ctx(includes=['mipsel_base'])
def mipsel_builder(c):
  pass

@config_ctx(includes=['main_builder'])
def dartium_builder(c):
  c.get_app_manifest_vars = False
  c.run_tree_truth = False
  c.deps_file = 'DEPS'
  c.managed = True

@config_ctx(includes=['main_builder'])
def cronet_builder(c):
  pass

@config_ctx(includes=['cronet_builder'])
def cronet_rel(c):
  pass

@config_ctx()
def arm_builder(c):
  pass

@config_ctx()
def x64_base(c):
  pass

@config_ctx(includes=['x64_base'])
def x64_builder(c):
  pass

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
  c.tests.append('smoke_instrumentation_tests')
  c.tests.append('small_instrumentation_tests')
  c.tests.append('medium_instrumentation_tests')
  c.tests.append('large_instrumentation_tests')

@config_ctx(includes=['instrumentation_tests'])
def main_tests(c):
  pass

@config_ctx(includes=['tests_base'])
def clang_tests(c):
  c.tests.append('smoke_instrumentation_tests')
  c.asan_symbolize = True

@config_ctx(includes=['tests_base'])
def enormous_tests(c):
  c.extra_deploy_opts = ['--await-internet']
  c.tests.append('enormous_instrumentation_tests')

@config_ctx(includes=['try_base', 'instrumentation_tests'])
def try_instrumentation_tests(c):
  pass

@config_ctx(includes=['x86_base', 'try_base', 'instrumentation_tests'])
def x86_try_instrumentation_tests(c):
  c.extra_deploy_opts.append('--non-rooted')

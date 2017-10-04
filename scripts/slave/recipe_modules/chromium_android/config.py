# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from recipe_engine.config import config_item_context, ConfigGroup
from recipe_engine.config import ConfigList, Dict, List, Single, Static
from recipe_engine.config_types import Path

def BaseConfig(CHECKOUT_PATH, INTERNAL=False, REPO_NAME=None, REPO_URL=None,
               BUILD_CONFIG='Debug', REVISION='', asan_symbolize=False,
               **_kwargs):
  return ConfigGroup(
    CHECKOUT_PATH = Static(CHECKOUT_PATH),
    INTERNAL = Static(INTERNAL),
    REPO_NAME = Static(REPO_NAME),
    REPO_URL = Static(REPO_URL),
    BUILD_CONFIG = Static(BUILD_CONFIG),
    cs_base_url = Single(basestring, required=False, empty_val='http://cs.chromium.org'),
    results_bucket = Single(basestring, required=False, empty_val='chromium-result-details'),
    revision = Single(basestring, empty_val=REVISION),
    revisions = Dict(value_type=(basestring, types.NoneType)),
    asan_symbolize = Single(bool, required=False, empty_val=asan_symbolize),
    get_app_manifest_vars = Single(bool, required=False, empty_val=True),
    run_tree_truth = Single(bool, required=False, empty_val=True),
    deps_file = Single(basestring, required=False, empty_val='.DEPS.git'),
    internal_dir_name = Single(basestring, required=False),
    # deps_dir: where to checkout the gclient deps file
    deps_dir = Single(basestring, required=False, empty_val=REPO_NAME),
    managed = Single(bool, required=False, empty_val=True),
    extra_deploy_opts = List(inner_type=basestring),
    tests = List(inner_type=basestring),
    cr_build_android = Static(CHECKOUT_PATH.join('build', 'android')),
    test_runner = Single(Path),
    gclient_custom_deps = Dict(value_type=(basestring, types.NoneType)),
    channel = Single(basestring, empty_val='chrome'),
    gclient_custom_vars = Dict(value_type=(basestring, types.NoneType)),
    coverage = Single(bool, required=False, empty_val=False),
    chrome_specific_wipe = Single(bool, required=False, empty_val=False),
    incremental_coverage = Single(bool, required=False, empty_val=False),
    env = ConfigGroup(
      LLVM_FORCE_HEAD_REVISION = Single(basestring, required=False),
    ),
    restart_usb = Single(bool, required=False, empty_val=False),
    use_devil_adb = Single(bool, required=False, empty_val=False),
    # TODO(jbudorick): Remove this once everything has switched to devil
    # provisioning.
    use_devil_provision = Single(bool, required=False, empty_val=False),
    remove_system_packages = List(inner_type=basestring),
  )


config_ctx = config_item_context(BaseConfig)

@config_ctx(is_root=True)
def base_config(c):
  c.internal_dir_name = 'clank'
  c.test_runner = c.CHECKOUT_PATH.join('build', 'android', 'test_runner.py')

@config_ctx()
def main_builder(c):
  pass

@config_ctx()
def main_builder_mb(c):
  pass

@config_ctx()
def main_builder_rel_mb(c):
  pass

@config_ctx()
def clang_builder(c):  # pragma: no cover
  pass

@config_ctx()
def clang_builder_mb(c):
  pass

@config_ctx(config_vars={'BUILD_CONFIG': 'Release'},
            includes=['asan_symbolize'])
def clang_asan_tot_release_builder(c):  # pragma: no cover
  c.env.LLVM_FORCE_HEAD_REVISION = 'YES'

@config_ctx(config_vars={'BUILD_CONFIG': 'Debug'})
def clang_tot_debug_builder(c):  # pragma: no cover
  c.env.LLVM_FORCE_HEAD_REVISION = 'YES'

@config_ctx(config_vars={'BUILD_CONFIG': 'Release'})
def clang_tot_release_builder(c):  # pragma: no cover
  c.env.LLVM_FORCE_HEAD_REVISION = 'YES'

@config_ctx(includes=['x64_builder_mb'])
def clang_builder_mb_x64(c):
  pass

@config_ctx()
def x86_base(c):
  pass

@config_ctx(includes=['x86_base'])
def x86_builder(c):
  pass

@config_ctx(includes=['x86_builder'])
def x86_builder_mb(c):
  pass

@config_ctx()
def mipsel_base(c):
  pass

@config_ctx(includes=['mipsel_base'])
def mipsel_builder(c):  # pragma: no cover
  pass

@config_ctx(includes=['mipsel_base'])
def mipsel_builder_mb(c):
  pass

@config_ctx(includes=['main_builder'])
def dartium_builder(c):  # pragma: no cover
  c.get_app_manifest_vars = False
  c.run_tree_truth = False
  if c.deps_dir != 'src/dart':
    c.deps_file = 'DEPS'
  else:
    c.deps_file = 'tools/deps/dartium.deps/DEPS'
  c.managed = True

@config_ctx()
def arm_l_builder(c):  # pragma: no cover
  pass

@config_ctx()
def arm_l_builder_lto(c):  # pragma: no cover
  pass

@config_ctx()
def arm_l_builder_rel(c):  # pragma: no cover
  pass

@config_ctx()
def arm_v6_builder_rel(c):  # pragma: no cover
  pass

@config_ctx()
def x64_base(c):
  pass

@config_ctx(includes=['x64_base'])
def x64_builder_mb(c):
  pass

@config_ctx()
def arm64_builder(c):
  pass

@config_ctx()
def arm64_builder_mb(c):
  pass

@config_ctx()
def arm64_builder_rel(c):  # pragma: no cover
  pass

@config_ctx()
def arm64_builder_rel_mb(c):
  pass

@config_ctx()
def try_base(c):
  pass  # pragma: no cover

@config_ctx(includes=['try_base'])
def try_builder(c):
  pass  # pragma: no cover

@config_ctx(includes=['x86_builder', 'try_builder'])
def x86_try_builder(c):
  pass  # pragma: no cover

@config_ctx()
def tests_base(c):  # pragma: no cover
  pass

@config_ctx(includes=['arm64_builder_rel'])
def tests_arm64(c):  # pragma: no cover
  pass

@config_ctx(includes=['x64_builder'])
def tests_x64(c):  # pragma: no cover
  pass

@config_ctx(includes=['tests_base'])
def instrumentation_tests(c):  # pragma: no cover
  c.tests.append('smoke_instrumentation_tests')
  c.tests.append('small_instrumentation_tests')
  c.tests.append('medium_instrumentation_tests')
  c.tests.append('large_instrumentation_tests')

@config_ctx(includes=['instrumentation_tests'])
def main_tests(c):
  pass  # pragma: no cover

@config_ctx(includes=['asan_symbolize', 'tests_base'])
def clang_tests(c):  # pragma: no cover
  c.tests.append('smoke_instrumentation_tests')

@config_ctx(includes=['tests_base'])
def enormous_tests(c):  # pragma: no cover
  c.extra_deploy_opts = ['--await-internet']
  c.tests.append('enormous_instrumentation_tests')

@config_ctx(includes=['try_base', 'instrumentation_tests'])
def try_instrumentation_tests(c):
  pass  # pragma: no cover

@config_ctx(includes=['x86_base', 'try_base', 'instrumentation_tests'])
def x86_try_instrumentation_tests(c):
  c.extra_deploy_opts.append('--non-rooted')  # pragma: no cover

@config_ctx(includes=['main_builder'])
def coverage_builder_tests(c):  # pragma: no cover
  pass

@config_ctx(includes=['main_builder'])
def non_device_wipe_provisioning(c):
  c.chrome_specific_wipe = True

@config_ctx(includes=['main_builder'])
def incremental_coverage_builder_tests(c):
  c.incremental_coverage = True

@config_ctx()
def chromium_perf(c):
  pass

@config_ctx()
def cast_builder(c):
  pass

@config_ctx()
def restart_usb(c):
  c.restart_usb = True

@config_ctx()
def use_devil_adb(c):
  c.use_devil_adb = True

@config_ctx()
def use_devil_provision(c):
  c.use_devil_provision = True

@config_ctx(includes=['use_devil_provision'])
def remove_system_vrcore(c):
  c.remove_system_packages.append('com.google.vr.vrcore')

@config_ctx(includes=['use_devil_provision'])
def remove_system_webview(c):
  c.remove_system_packages.extend(
      ['com.google.android.webview', 'com.android.webview'])

@config_ctx(includes=['use_devil_provision'])
def remove_system_webview_shell(c):
  c.remove_system_packages.append('org.chromium.webview_shell')

@config_ctx(includes=['use_devil_provision'])
def remove_system_chrome(c):
  c.remove_system_packages.append('com.android.chrome')

@config_ctx(includes=[
    'remove_system_chrome',
    'remove_system_webview',
    'remove_system_webview_shell'])
def remove_all_system_webviews(c):
  pass

@config_ctx()
def asan_symbolize(c):  # pragma: no cover
  c.asan_symbolize = True


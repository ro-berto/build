# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.android.android_recipe_common import AndroidRecipeCommon

def GetSteps(api):
  android_common = AndroidRecipeCommon(api, lunch_flavor='full-eng')
  android_repo_url = 'https://android.googlesource.com/platform/manifest'
  android_repo_branch = 'jb-mr1.1-dev'
  android_ndk_pin_revision = '5049b437591600fb0d262e4215cee4226e63c6ce'
  android_repo_sync_flags = ['-j16', '-d', '-f']

  chromium_solution_name = 'src'
  chromium_checkout_revision = None
  if 'revision' in api.properties:
    chromium_checkout_revision = '%s@%s' % (chromium_solution_name,
                                            api.properties['revision'])
  compile_step = android_common.gen_compile_step(
      step_name='compile',
      build_tool='make-android',
      targets=['libwebviewchromium', 'android_webview_java'],
      use_goma=True)

  return (
    android_common.gen_sync_chromium_with_empty_deps_step(
        svn_revision=chromium_checkout_revision),
    android_common.gen_calculate_trimmed_deps_step(),
    android_common.gen_sync_chromium_with_trimmed_deps_step(
        svn_revision=chromium_checkout_revision),
    android_common.gen_lastchange_steps(),
    android_common.gen_repo_init_steps(android_repo_url, android_repo_branch),
    android_common.gen_generate_local_manifest_step(
            ndk_pin_revision=android_ndk_pin_revision),
    android_common.gen_repo_sync_steps(android_repo_sync_flags),
    android_common.gen_symlink_chromium_into_android_tree_step(),
    android_common.gen_gyp_webview_step(),
    compile_step
  )

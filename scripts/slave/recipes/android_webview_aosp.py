# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.android.android_recipe_common import AndroidRecipeCommon

def GetSteps(api):
  android_lunch_flavor = api.properties.get('android_lunch_flavor', 'full-eng')
  android_ndk_pin_revision = api.properties.get('android_ndk_pin_revision')
  android_repo_url = api.properties.get('android_repo_url')
  android_repo_sync_flags = api.properties.get('android_repo_sync_flags',
                                               ['-j16', '-d', '-f'])
  android_repo_resync_projects = (
    api.properties.get('android_repo_resync_projects'))
  android_repo_branch = api.properties.get('android_repo_branch')

  slave_android_root_name = 'android-src'
  chromium_in_android_subpath = 'external/chromium_org'
  slave_chromium_in_android_path = api.slave_build_path(
      slave_android_root_name, chromium_in_android_subpath)

  android_common = AndroidRecipeCommon(
      api, slave_android_root_name, android_lunch_flavor)

  lastchange_command = [api.checkout_path('build', 'util', 'lastchange.py')]

  chromium_solution_name = 'src'
  chromium_checkout_revision = None
  if 'revision' in api.properties:
    chromium_checkout_revision = '%s@%s' % (chromium_solution_name,
                                            api.properties['revision'])

  empty_deps_spec = api.gclient_configs.chromium_bare(
      api.gclient_configs.BaseConfig(api.properties.get('use_mirror', True)))
  empty_deps_spec.solutions[0].deps_file = ''
  sync_chromium_with_empty_deps_step = api.gclient_checkout(
      empty_deps_spec, spec_name='empty_deps',
      svn_revision=chromium_checkout_revision)

  # For the android_webview AOSP build we want to only include whitelisted
  # DEPS. This is to detect the addition of unexpected new deps to the webview.
  calculate_trimmed_deps_step_name = 'calculate trimmed deps'
  calculate_trimmed_deps_step = api.step(
      calculate_trimmed_deps_step_name,
      [api.checkout_path('android_webview', 'buildbot', 'deps_whitelist.py'),
       '--method', 'android_build',
       '--path-to-deps', api.checkout_path('DEPS'),
      ],
      add_json_output=True)

  def sync_chromium_with_trimmed_deps_step(step_history, _failure):
    deps_blacklist_step = step_history[calculate_trimmed_deps_step_name]
    deps_blacklist = deps_blacklist_step.json_data['blacklist']
    cfg = api.gclient_configs.BaseConfig(
        api.properties.get('use_mirror', True))
    spec = api.gclient_configs.chromium_bare(cfg)
    spec.solutions[0].custom_deps = deps_blacklist
    spec.target_os = ['android']
    yield api.gclient_checkout(spec, spec_name='trimmed',
                               svn_revision=chromium_checkout_revision)

  lastchange_steps = [
      api.step('Chromium LASTCHANGE', lastchange_command + [
          '-o', api.checkout_path('build', 'util', 'LASTCHANGE'),
          '-s', api.checkout_path()]),
      api.step('Blink LASTCHANGE', lastchange_command + [
          '-o', api.checkout_path('build', 'util', 'LASTCHANGE.blink'),
          '-s', api.checkout_path('third_party', 'WebKit')])
  ]

  local_manifest_ndk_pin_revision = []
  if android_ndk_pin_revision:
    local_manifest_ndk_pin_revision = ['--ndk-revision',
                                       android_ndk_pin_revision]
  generate_local_manifest_step = api.step(
      'generate local manifest', [
          api.checkout_path('android_webview', 'buildbot',
                            'generate_local_manifest.py'),
          android_common.build_path, chromium_in_android_subpath] +
      local_manifest_ndk_pin_revision)

  # If the repo sync flag override specifies a smart sync manifest, then this
  # makes it possible to sync specific projects past the smart sync manifest
  # to the most up-to-date version.
  android_repo_resync_projects_steps = []
  if android_repo_resync_projects:
    for project in android_repo_resync_projects:
      android_repo_resync_projects_steps.append(
        api.step('repo re-sync project ' + project,
                 [android_common.repo_path, 'sync', project],
                 cwd=android_common.build_path))

  remove_potentially_stale_android_chromium_org_step = []
  if api.path_exists(slave_chromium_in_android_path):
    remove_potentially_stale_android_chromium_org_step = [
      api.step('remove chromium_org',
               ['rm', '-rf', slave_chromium_in_android_path]),
    ]

  symlink_chromium_into_android_tree_step = [
    api.step('symlink chromium_org',
             ['ln', '-s', api.checkout_path(), slave_chromium_in_android_path]),
  ]

  gyp_webview_step = [
    api.step('gyp_webview', android_common.with_lunch_command + [
             api.slave_build_path(
               slave_android_root_name, 'external', 'chromium_org',
               'android_webview', 'tools', 'gyp_webview')],
             cwd=slave_chromium_in_android_path),
  ]

  compile_step = android_common.gen_compile_step(
      step_name='compile',
      build_tool='make-android',
      targets=['libwebviewchromium', 'android_webview_java'],
      use_goma=True)

  return (
    sync_chromium_with_empty_deps_step,
    calculate_trimmed_deps_step,
    sync_chromium_with_trimmed_deps_step,
    lastchange_steps,
    android_common.gen_repo_init_steps(android_repo_url, android_repo_branch),
    generate_local_manifest_step,
    android_common.gen_repo_sync_steps(android_repo_sync_flags),
    android_repo_resync_projects_steps,
    remove_potentially_stale_android_chromium_org_step,
    symlink_chromium_into_android_tree_step,
    gyp_webview_step,
    compile_step
  )

# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def GetSteps(api, factory_properties, build_properties):
  android_lunch_flavor = factory_properties.get('android_lunch_flavor',
                                                'full-eng')
  android_ndk_pin_revision = factory_properties.get('android_ndk_pin_revision')
  android_repo_url = factory_properties.get('android_repo_url')
  android_repo_sync_flags = factory_properties.get('android_repo_sync_flags',
                                                   ['-j16', '-d', '-f'])
  android_repo_resync_projects = factory_properties.get(
      'android_repo_resync_projects')
  android_repo_branch = factory_properties.get('android_repo_branch')

  slave_android_root_name = 'android-src'
  slave_android_build_path = api.slave_build_path(slave_android_root_name)
  slave_android_out_path = api.slave_build_path(slave_android_root_name, 'out')
  chromium_in_android_subpath = 'external/chromium_org'
  slave_chromium_in_android_path = api.slave_build_path(
      slave_android_root_name, chromium_in_android_subpath)
  slave_repo_in_android_path = api.slave_build_path(slave_android_root_name,
                                                    '.repo', 'repo', 'repo')
  slave_repo_copy_dir = api.slave_build_path('repo_copy')
  slave_repo_copy_path = api.slave_build_path('repo_copy', 'repo')

  steps = api.Steps(build_properties)

  # Some commands need to be run after lunch has been executed to set up the
  # Android-specific environment variables.
  with_lunch_command = [api.build_path('scripts', 'slave', 'android',
                                       'with_lunch'),
                        slave_android_build_path,
                        android_lunch_flavor]

  # In order to get at the DEPS whitelist file we first need a bare checkout.
  bare_chromium_spec = {'solutions': [
    {
      'name': 'src',
      'url': steps.ChromiumSvnURL('chrome', 'trunk', 'src'),
      'deps_file': '',
      'managed': True,
      'safesync_url': '',
    }]}
  sync_chromium_bare_step = steps.gclient_checkout(bare_chromium_spec,
                                                   spec_name='bare')

  # For the android_webview AOSP build we want to only include whitelisted
  # DEPS. This is to detect the addition of unexpected new deps to the webview.
  calculate_trimmed_deps_step_name = 'calculate trimmed deps'
  calculate_trimmed_deps_step = steps.step(
      calculate_trimmed_deps_step_name,
      [api.checkout_path('android_webview', 'buildbot', 'deps_whitelist.py'),
       '--method', 'android_build',
       '--path-to-deps', api.checkout_path('DEPS'),
      ],
      add_json_output=True)

  def sync_chromium_with_trimmed_deps_step(step_history, _failure):
    deps_blacklist_step = step_history[calculate_trimmed_deps_step_name]
    deps_blacklist = deps_blacklist_step.json_data['blacklist']
    trimmed_chromium_spec = {
        'solutions': [{
            'name' : 'src',
            'url' : steps.ChromiumSvnURL('chrome', 'trunk', 'src'),
            'safesync_url': '',
            'custom_deps': deps_blacklist,
            }],
        'target_os': ['android'],
        }
    yield steps.gclient_checkout(trimmed_chromium_spec, spec_name='trimmed')

  gclient_runhooks_step = steps.step(
      'gclient runhooks',
      [api.depot_tools_path('gclient'), 'runhooks'])

  # The version of repo checked into depot_tools doesn't support switching
  # between branches correctly due to
  # https://code.google.com/p/git-repo/issues/detail?id=46 which is why we use
  # the copy of repo from the Android tree.
  # The copy of repo from depot_tools is only used to bootstrap the Android
  # tree checkout.
  repo_init_steps = []

  repo_path = api.depot_tools_path('repo')
  if api.path_exists(slave_repo_in_android_path):
    repo_path = slave_repo_copy_path
    if not api.path_exists(slave_repo_copy_dir):
      repo_init_steps.append(
          steps.step('mkdir repo copy dir',
                     ['mkdir', '-p', slave_repo_copy_dir]))
    repo_init_steps.append(
        steps.step('copy repo from Android', [
            'cp', slave_repo_in_android_path, slave_repo_copy_path]))

  if not api.path_exists(slave_android_build_path):
    repo_init_steps.append(
      steps.step('mkdir android source root', [
          'mkdir', slave_android_build_path]))

  repo_init_steps.append(
    steps.step('repo init', [
        repo_path,
        'init',
        '-u', android_repo_url,
        '-b', android_repo_branch],
      cwd=slave_android_build_path))

  local_manifest_ndk_pin_revision = []
  if android_ndk_pin_revision:
    local_manifest_ndk_pin_revision = ['--ndk-revision',
                                       android_ndk_pin_revision]
  generate_local_manifest_step = steps.step(
      'generate local manifest', [
          api.checkout_path('android_webview', 'buildbot',
                            'generate_local_manifest.py'),
          slave_android_build_path, chromium_in_android_subpath] +
      local_manifest_ndk_pin_revision)

  repo_sync_step = steps.step('repo sync',
                              [repo_path, 'sync'] + android_repo_sync_flags,
                              cwd=slave_android_build_path),

  # If the repo sync flag override specifies a smart sync manifest, then this
  # makes it possible to sync specific projects past the smart sync manifest
  # to the most up-to-date version.
  android_repo_resync_projects_steps = []
  if android_repo_resync_projects:
    for project in android_repo_resync_projects:
      android_repo_resync_projects_steps.append(
        steps.step('repo re-sync project ' + project,
                   [repo_path, 'sync', project],
                   cwd=slave_android_build_path))

  remove_potentially_stale_android_chromium_org_step = []
  if api.path_exists(slave_chromium_in_android_path):
    remove_potentially_stale_android_chromium_org_step = [
      steps.step('remove chromium_org',
                 ['rm', '-rf', slave_chromium_in_android_path]),
    ]

  symlink_chromium_into_android_tree_step = [
    steps.step('symlink chromium_org',
               ['ln', '-s', api.checkout_path(),
                slave_chromium_in_android_path]),
  ]

  gyp_webview_step = [
    steps.step('gyp_webview', with_lunch_command + [
               api.slave_build_path(
                 slave_android_root_name, 'external', 'chromium_org',
                 'android_webview', 'tools', 'gyp_webview')],
               cwd=slave_chromium_in_android_path),
  ]

  compile_compiler_options = []
  if api.path_exists(api.build_path('goma')):
    compile_compiler_options = ['--compiler', 'goma',
                                '--goma-dir', api.build_path('goma')]
  compile_step = [
      steps.step('compile', with_lunch_command +
                 [api.build_path('scripts', 'slave', 'compile.py'),
                  'libwebviewchromium', 'android_webview_java',
                  '--build-dir', api.slave_build_path(),
                  '--src-dir', slave_android_build_path,
                  '--target-output-dir', slave_android_out_path,
                  '--build-tool', 'make-android',
                  '--verbose'] + compile_compiler_options,
                 cwd=api.SLAVE_BUILD_ROOT),
  ]

  return (
    sync_chromium_bare_step,
    calculate_trimmed_deps_step,
    sync_chromium_with_trimmed_deps_step,
    gclient_runhooks_step,
    repo_init_steps,
    generate_local_manifest_step,
    repo_sync_step,
    android_repo_resync_projects_steps,
    remove_potentially_stale_android_chromium_org_step,
    symlink_chromium_into_android_tree_step,
    gyp_webview_step,
    compile_step
  )

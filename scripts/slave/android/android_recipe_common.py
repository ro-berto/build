# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common steps for recipes that sync/build Android sources."""

class AndroidRecipeCommon(object):
  def __init__(self, api, lunch_flavor='full-eng'):
    self._api = api
    self._slave_android_root_name = 'android-src'
    self._chromium_in_android_subpath = 'external/chromium_org'
    self._calculate_trimmed_deps_step_name = 'calculate trimmed deps'

    self._slave_chromium_in_android_path = api.slave_build_path(
        self._slave_android_root_name, self._chromium_in_android_subpath)

    self._slave_android_build_path = api.slave_build_path(
        self._slave_android_root_name)
    self._slave_android_out_path = api.slave_build_path(
        self._slave_android_root_name, 'out')
    self._lunch_flavor = lunch_flavor
    self._repo_path = None

  @property
  def repo_path(self):
    return self._repo_path

  @property
  def android_root_name(self):
    return self._slave_android_root_name

  @property
  def with_lunch_command(self):
    return [self._api.build_path('scripts', 'slave', 'android', 'with_lunch'),
            self._slave_android_build_path,
            self._lunch_flavor]

  @property
  def lastchange_command(self):
    return [self._api.checkout_path('build', 'util', 'lastchange.py')]

  @property
  def build_path(self):
    return self._slave_android_build_path

  def gen_sync_chromium_with_empty_deps_step(self, svn_revision=None):
    cfg = self._api.gclient_configs.BaseConfig(
        self._api.properties.get('use_mirror', True))
    empty_deps_spec = self._api.gclient_configs.chromium_bare(cfg)
    empty_deps_spec.solutions[0].deps_file = ''
    return self._api.gclient_checkout(empty_deps_spec, spec_name='empty_deps',
                                      svn_revision=svn_revision)

  def gen_calculate_trimmed_deps_step(self):
    # For the android_webview AOSP build we want to only include whitelisted
    # DEPS. This is to detect the addition of unexpected new deps to the
    # webview.
    return self._api.step(
        self._calculate_trimmed_deps_step_name,
        [self._api.checkout_path('android_webview', 'buildbot',
                                 'deps_whitelist.py'),
         '--method', 'android_build',
         '--path-to-deps', self._api.checkout_path('DEPS'),
        ],
        add_json_output=True)

  def gen_sync_chromium_with_trimmed_deps_step(self, svn_revision=None):
    def sync_chromium_with_trimmed_deps_step(step_history, _failure):
      deps_blacklist_step = step_history[self._calculate_trimmed_deps_step_name]
      deps_blacklist = deps_blacklist_step.json_data['blacklist']
      cfg = self._api.gclient_configs.BaseConfig(
          self._api.properties.get('use_mirror', True))
      spec = self._api.gclient_configs.chromium_bare(cfg)
      spec.solutions[0].custom_deps = deps_blacklist
      spec.target_os = ['android']
      yield self._api.gclient_checkout(spec, spec_name='trimmed',
                                       svn_revision=svn_revision)
    return sync_chromium_with_trimmed_deps_step

  def gen_lastchange_steps(self):
    return [
        self._api.step('Chromium LASTCHANGE', self.lastchange_command + [
            '-o', self._api.checkout_path('build', 'util', 'LASTCHANGE'),
            '-s', self._api.checkout_path()]),
        self._api.step('Blink LASTCHANGE', self.lastchange_command + [
            '-o', self._api.checkout_path('build', 'util', 'LASTCHANGE.blink'),
            '-s', self._api.checkout_path('third_party', 'WebKit')])
    ]

  def gen_repo_init_steps(self, android_repo_url, android_repo_branch):
    # The version of repo checked into depot_tools doesn't support switching
    # between branches correctly due to
    # https://code.google.com/p/git-repo/issues/detail?id=46 which is why we use
    # the copy of repo from the Android tree.
    # The copy of repo from depot_tools is only used to bootstrap the Android
    # tree checkout.
    repo_in_android_path = self._api.slave_build_path(
        self._slave_android_root_name, '.repo', 'repo', 'repo')
    repo_copy_dir = self._api.slave_build_path('repo_copy')
    repo_copy_path = self._api.slave_build_path('repo_copy', 'repo')
    repo_init_steps = []
    self._repo_path = self._api.depot_tools_path('repo')
    if self._api.path_exists(repo_in_android_path):
      self._repo_path = repo_copy_path
      if not self._api.path_exists(repo_copy_dir):
        repo_init_steps.append(
            self._api.step('mkdir repo copy dir',
                           ['mkdir', '-p', repo_copy_dir]))
      repo_init_steps.append(
          self._api.step('copy repo from Android', [
            'cp', repo_in_android_path, repo_copy_path]))
    if not self._api.path_exists(self._slave_android_build_path):
      repo_init_steps.append(
        self._api.step('mkdir android source root', [
            'mkdir', self._slave_android_build_path]))
    repo_init_steps.append(
      self._api.step('repo init', [
                     self._repo_path,
                     'init',
                     '-u', android_repo_url,
                     '-b', android_repo_branch],
                     cwd=self._slave_android_build_path))
    return repo_init_steps

  def gen_generate_local_manifest_step(self, ndk_pin_revision=None):
    local_manifest_ndk_pin_revision = []
    if ndk_pin_revision:
      local_manifest_ndk_pin_revision = ['--ndk-revision',
                                         ndk_pin_revision]
    return self._api.step(
        'generate local manifest', [
            self._api.checkout_path('android_webview', 'buildbot',
                              'generate_local_manifest.py'),
            self.build_path, self._chromium_in_android_subpath] +
        local_manifest_ndk_pin_revision)

  def gen_repo_sync_steps(self, flags):
    # gen_repo_init_steps must have been invoked first.
    assert(self._repo_path != None)
    return [self._api.step('repo sync',
                           [self.repo_path, 'sync'] + flags,
                           cwd=self._slave_android_build_path)]

  def gen_symlink_chromium_into_android_tree_step(self):
    def symlink_chromium_into_android_tree_step(_step_history, _failure):
      if self._api.path_exists(self._slave_chromium_in_android_path):
        yield self._api.step('remove chromium_org',
                   ['rm', '-rf', self._slave_chromium_in_android_path])

      yield self._api.step('symlink chromium_org', [
          'ln', '-s',
          self._api.checkout_path(),
          self._slave_chromium_in_android_path]),
    return symlink_chromium_into_android_tree_step

  def gen_gyp_webview_step(self):
    return self._api.step('gyp_webview', self.with_lunch_command + [
             self._api.slave_build_path(
               self._slave_android_root_name, 'external', 'chromium_org',
               'android_webview', 'tools', 'gyp_webview')],
             cwd=self._slave_chromium_in_android_path),

  def gen_compile_step(self, step_name, build_tool, targets=None,
                     use_goma=True, src_dir=None, target_out_dir=None,
                     envsetup=None):
    src_dir = src_dir or self._slave_android_build_path
    target_out_dir = target_out_dir or self._slave_android_out_path
    envsetup = envsetup or self.with_lunch_command
    targets = targets or []
    compiler_option = []
    compile_script = [self._api.build_path('scripts', 'slave', 'compile.py')]
    if use_goma and self._api.path_exists(self._api.build_path('goma')):
      compiler_option = ['--compiler', 'goma',
                         '--goma-dir', self._api.build_path('goma')]
    return [self._api.step(step_name,
                           envsetup +
                           compile_script +
                           targets +
                           ['--build-dir', self._api.slave_build_path()] +
                           ['--src-dir', src_dir] +
                           ['--target-output-dir', target_out_dir] +
                           ['--build-tool', build_tool] +
                           ['--verbose'] +
                           compiler_option,
                           cwd=self._api.slave_build_path())]

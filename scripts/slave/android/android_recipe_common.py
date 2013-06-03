# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common steps for recipes that sync/build Android sources."""

class AndroidRecipeCommon(object):
  def __init__(self, api, steps, android_root_name, lunch_flavor):
    self._api = api
    self._steps = steps
    self._root_name = android_root_name
    self._build_path = api.slave_build_path(android_root_name)
    self._out_path = api.slave_build_path(android_root_name, 'out')
    self._lunch_flavor = lunch_flavor
    self._repo_path = None

  @property
  def repo_path(self):
    return self._repo_path

  @property
  def with_lunch_command(self):
    return [self._api.build_path('scripts', 'slave', 'android', 'with_lunch'),
            self._build_path,
            self._lunch_flavor]

  @property
  def build_path(self):
    return self._build_path

  def gen_repo_init_steps(self, android_repo_url, android_repo_branch):
    # The version of repo checked into depot_tools doesn't support switching
    # between branches correctly due to
    # https://code.google.com/p/git-repo/issues/detail?id=46 which is why we use
    # the copy of repo from the Android tree.
    # The copy of repo from depot_tools is only used to bootstrap the Android
    # tree checkout.
    repo_in_android_path = self._api.slave_build_path(
        self._root_name, '.repo', 'repo', 'repo')
    repo_copy_dir = self._api.slave_build_path('repo_copy')
    repo_copy_path = self._api.slave_build_path('repo_copy', 'repo')
    repo_init_steps = []
    self._repo_path = self._api.depot_tools_path('repo')
    if self._api.path_exists(repo_in_android_path):
      self._repo_path = repo_copy_path
      if not self._api.path_exists(repo_copy_dir):
        repo_init_steps.append(
            self._steps.step('mkdir repo copy dir',
                       ['mkdir', '-p', repo_copy_dir]))
      repo_init_steps.append(
          self._steps.step('copy repo from Android', [
              'cp', repo_in_android_path, repo_copy_path]))
    if not self._api.path_exists(self._build_path):
      repo_init_steps.append(
        self._steps.step('mkdir android source root', [
            'mkdir', self._build_path]))
    repo_init_steps.append(
      self._steps.step('repo init', [
                       self._repo_path,
                       'init',
                       '-u', android_repo_url,
                       '-b', android_repo_branch],
                       cwd=self._build_path))
    return repo_init_steps

  def gen_repo_sync_steps(self, flags):
    # gen_repo_init_steps must have been invoked first.
    assert(self._repo_path != None)
    return [self._steps.step('repo sync',
                             [self.repo_path, 'sync'] + flags,
                             cwd=self._build_path)]

  def gen_compile_step(self, step_name, build_tool, targets=None,
                     use_goma=True, src_dir=None, target_out_dir=None,
                     envsetup=None):
    src_dir = src_dir or self._build_path
    target_out_dir = target_out_dir or self._out_path
    envsetup = envsetup or self.with_lunch_command
    targets = targets or []
    compiler_option = []
    compile_script = [self._api.build_path('scripts', 'slave', 'compile.py')]
    if use_goma and self._api.path_exists(self._api.build_path('goma')):
      compiler_option = ['--compiler', 'goma',
                         '--goma-dir', self._api.build_path('goma')]
    return [self._steps.step(step_name,
                             envsetup +
                             compile_script +
                             targets +
                             ['--build-dir', self._api.slave_build_path()] +
                             ['--src-dir', src_dir] +
                             ['--target-output-dir', target_out_dir] +
                             ['--build-tool', build_tool] +
                             ['--verbose'] +
                             compiler_option,
                             cwd=self._api.SLAVE_BUILD_ROOT)]
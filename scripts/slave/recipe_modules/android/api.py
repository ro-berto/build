# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common steps for recipes that sync/build Android sources."""

from slave import recipe_api

class AOSPApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(AOSPApi, self).__init__(**kwargs)
    self._repo_path = None

  @property
  def with_lunch_command(self):
    return [self.m.path.build('scripts', 'slave', 'android', 'with_lunch'),
            self.c.build_path,
            self.c.lunch_flavor]

  @recipe_api.inject_test_data
  def calculate_trimmed_deps(self):
    return self.m.step(
      'calculate trimmed deps',
      [
        self.m.path.checkout('android_webview', 'buildbot',
                             'deps_whitelist.py'),
        '--method', 'android_build',
        '--path-to-deps', self.m.path.checkout('DEPS'),
        '--output-json', self.m.json.output()
      ],
    )

  def chromium_with_trimmed_deps(self, use_revision=True):
    svn_revision = 'HEAD'
    if use_revision and 'revision' in self.m.properties:
      svn_revision = str(self.m.properties['revision'])

    spec = self.m.gclient.make_config('chromium_empty')
    spec.solutions[0].revision = svn_revision
    self.m.gclient.spec_alias = 'empty_deps'
    yield self.m.gclient.checkout(spec)

    yield self.calculate_trimmed_deps()

    spec = self.m.gclient.make_config('chromium_bare')
    deps_blacklist = self.m.step_history.last_step().json.output['blacklist']
    spec.solutions[0].custom_deps = deps_blacklist
    spec.solutions[0].revision = svn_revision
    spec.target_os = ['android']
    self.m.gclient.spec_alias = 'trimmed'
    yield self.m.gclient.checkout(spec)
    del self.m.gclient.spec_alias

  def lastchange_steps(self):
    lastchange_command = self.m.path.checkout('build', 'util', 'lastchange.py')
    yield (
      self.m.step('Chromium LASTCHANGE', [
        lastchange_command,
        '-o', self.m.path.checkout('build', 'util', 'LASTCHANGE'),
        '-s', self.m.path.checkout]),
      self.m.step('Blink LASTCHANGE', [
        lastchange_command,
        '-o', self.m.path.checkout('build', 'util', 'LASTCHANGE.blink'),
        '-s', self.m.path.checkout('third_party', 'WebKit')])
    )

  # TODO(iannucci): Refactor repo stuff into another module?
  def repo_init_steps(self):
    # If a local_manifest.xml file is present and contains invalid entries init
    # and sync might fail.
    yield self.m.python.inline(
      'remove local_manifest.xml',
      """
        import os, sys

        to_delete = sys.argv[1]
        if os.path.exists(to_delete):
          os.unlink(to_delete)
      """,
      args=[self.c.build_path('.repo', 'local_manifest.xml')]
    )
    # The version of repo checked into depot_tools doesn't support switching
    # between branches correctly due to
    # https://code.google.com/p/git-repo/issues/detail?id=46 which is why we use
    # the copy of repo from the Android tree.
    # The copy of repo from depot_tools is only used to bootstrap the Android
    # tree checkout.
    repo_in_android_path = self.c.build_path('.repo', 'repo', 'repo')
    repo_copy_dir = self.m.path.slave_build('repo_copy')
    repo_copy_path = self.m.path.slave_build('repo_copy', 'repo')
    if self.m.path.exists(repo_in_android_path):
      yield self.m.path.makedirs('repo copy dir', repo_copy_dir)
      yield self.m.step('copy repo from Android', [
        'cp', repo_in_android_path, repo_copy_path])
      self.m.repo.repo_path = repo_copy_path
    yield self.m.path.makedirs('android source root', self.c.build_path)
    yield self.m.repo.init(self.c.repo.url, '-b', self.c.repo.branch,
                           cwd=self.c.build_path)
    self.m.path.mock_add_paths(repo_in_android_path)

  def generate_local_manifest_step(self):
    yield self.m.step(
        'generate local manifest', [
          self.m.path.checkout('android_webview', 'buildbot',
                               'generate_local_manifest.py'),
          self.c.build_path,
          self.c.chromium_in_android_subpath])

  def repo_sync_steps(self):
    # If external/chromium_org is a symlink this prevents repo from trying to
    # update the symlink's target (which might be an svn checkout).
    yield self.m.python.inline(
      'remove chromium_org symlink',
      """
        import os, sys

        to_delete = sys.argv[1]
        if os.path.exists(to_delete) and os.path.islink(to_delete):
          os.unlink(to_delete)
      """,
      args = [self.c.slave_chromium_in_android_path]
    )
    # repo_init_steps must have been invoked first.
    yield self.m.repo.sync(*self.c.repo.sync_flags, cwd=self.c.build_path)

  def symlink_chromium_into_android_tree_step(self):
    if self.m.path.exists(self.c.slave_chromium_in_android_path):
      yield self.m.step('remove chromium_org',
                      ['rm', '-rf', self.c.slave_chromium_in_android_path])
    yield self.m.step('symlink chromium_org', [
      'ln', '-s',
      self.m.path.checkout,
      self.c.slave_chromium_in_android_path]),

  def gyp_webview_step(self):
    yield self.m.step('gyp_webview', self.with_lunch_command + [
      self.c.slave_chromium_in_android_path('android_webview', 'tools',
                                            'gyp_webview')],
      cwd=self.c.slave_chromium_in_android_path)

  def compile_step(self, build_tool, step_name='compile', targets=None,
                   use_goma=True, src_dir=None, target_out_dir=None,
                   envsetup=None):
    src_dir = src_dir or self.c.build_path
    target_out_dir = target_out_dir or self.c.slave_android_out_path
    envsetup = envsetup or self.with_lunch_command
    targets = targets or []
    compiler_option = []
    compile_script = [self.m.path.build('scripts', 'slave', 'compile.py')]
    if use_goma and self.m.path.exists(self.m.path.build('goma')):
      compiler_option = ['--compiler', 'goma',
                         '--goma-dir', self.m.path.build('goma')]
    yield self.m.step(step_name,
                      envsetup +
                      compile_script +
                      targets +
                      ['--build-dir', self.m.path.slave_build] +
                      ['--src-dir', src_dir] +
                      ['--build-tool', build_tool] +
                      ['--verbose'] +
                      compiler_option,
                      cwd=self.m.path.slave_build)


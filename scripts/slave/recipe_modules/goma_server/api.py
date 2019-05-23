# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class GomaServerApi(recipe_api.RecipeApi):
  """
  GomaServerApi contains helper functions for building goma server.
  """

  def __init__(self, **kwargs):
    super(GomaServerApi, self).__init__(**kwargs)

  def BuildAndTest(self, repository, package_base, path, allow_diff=True):
    """Build goma server and run test.

    Args:
      repository: Goma server repository URL in str.
      package_base: package base name of goma server in str.
      path: PATH environment to be used in the build in str list.
            go and protoc should be available in PATH.
    """
    build_root = self.m.path['cache'].join('builder')
    goma_src_dir = build_root.join('goma_src')
    gopath_dir = build_root.join('go')
    env_prefixes = {
        'GOPATH': [gopath_dir],
        'PATH': path + [gopath_dir.join('bin')],
    }
    env = {
        'GO111MODULE': 'on',
    }

    # Checkout
    # We do not have CI builder, but let me confirm.
    assert self.m.tryserver.is_tryserver
    ref = self.m.tryserver.gerrit_change_fetch_ref
    self.m.git.checkout(repository, ref=ref, dir_path=goma_src_dir)

    with self.m.context(cwd=self.m.path['checkout'],
                     env_prefixes=env_prefixes,
                     env=env):
      # Set up modules.
      self.m.step('list modules',
                  ['go', 'list', '-m', 'all'])
      # Generate proto
      self.m.step('generate proto',
                  ['go', 'generate',
                   self.m.path.join(package_base, 'proto', '...')])
      # Build
      self.m.step('build',
                  ['go', 'install',
                   self.m.path.join(package_base, 'cmd', '...')])
      # Test
      self.m.step('test',
                  ['go', 'test', '-race', '-cover',
                   self.m.path.join(package_base, '...')])
      # Vet
      self.m.step('go vet',
                  ['go', 'vet', self.m.path.join(package_base, '...')])
      # Go fmt
      self.m.step('go fmt',
                  ['go', 'fmt', self.m.path.join(package_base, '...')])
      # Check diff
      git_diff_arg = ['diff']
      if not allow_diff:
        git_diff_arg.append('--exit-code')
      self.m.git(*git_diff_arg, name='check git diff')

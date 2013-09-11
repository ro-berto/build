# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class ChromiteApi(recipe_api.RecipeApi):
  manifest_url = 'https://chromium.googlesource.com/chromiumos/manifest.git'
  repo_url = 'https://chromium.googlesource.com/external/repo.git'
  chromite_subpath = 'chromite'

  def checkout(self, manifest_url=None, repo_url=None):
    manifest_url = manifest_url or self.manifest_url
    repo_url = repo_url or self.repo_url

    return (
      self.m.repo.init(manifest_url, '--repo-url', repo_url),
      self.m.repo.sync(),
    )

  def cros_sdk(self, name, cmd, chromite_path=None, **kwargs):
    """Return a step to run a command inside the cros_sdk."""
    chromite_path = (chromite_path or
                     self.m.path.slave_build(self.chromite_subpath))
    return self.m.python(
      name,
      [self.m.path.join(chromite_path, 'bin', 'cros_sdk'), '--'] + cmd,
      **kwargs
    )

  def setup_board(self, board, **kwargs):
    """Run the setup_board script inside the chroot."""
    return self.cros_sdk('setup board',
                         ['./setup_board', '--board', board],
                         **kwargs)

  def build_packages(self, board, **kwargs):
    """Run the build_packages script inside the chroot."""
    return self.cros_sdk('build packages',
                         ['./build_packages', '--board', board],
                         **kwargs)

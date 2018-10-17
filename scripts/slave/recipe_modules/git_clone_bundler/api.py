# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
The 'git_clone_bundler' creates and uploads 'clone.bundle' packages to
Google Storage for specified Git repositories.
"""

import hashlib

from recipe_engine import recipe_api


class GitCloneBundlerApi(recipe_api.RecipeApi):
  """Provides methods to encapsulate repo operations."""

  def __init__(self, **kwargs):
    super(recipe_api.RecipeApi, self).__init__(**kwargs)

  @property
  def base_path(self):
    return self.m.path['start_dir'].join('git_clone_bundler')

  @property
  def bundle_dir(self):
    return self.base_path.join('bundles')

  @staticmethod
  def _hashname(base):
    return hashlib.md5(base).hexdigest()

  def _setup(self):
    self.m.file.rmtree('remove old bundles', self.bundle_dir)
    self.m.file.ensure_directory('make bundles dir', self.bundle_dir)

  def _bundle(self, git_path, gs_bucket, gs_subpath, name, unauthenticated_url):
    """
    Creates a Git bundle from a Git repository and uploads it to Google Storage.

    Args:
      git_path: (Path) The path of the Git repository to bundle.
      gs_bucket: (str) The name of the Google Storage bucket.
      gs_subpath: (str) The path within the Google Storage bucket.
r     name (str): If not None, the name of this bundle operation (to
          differentiate steps).
      unauthenticated_url: (bool) If True, request an unauthenticated URL from
          Google Storage.

    Returns: (str) The Google Storage URL where the bundle was uploaded.
    """
    # Function to generate step names.
    def s(base):
      if name:
        return '%s (%s)' % (base, name)
      return base

    # Build the upload path. This will be used to create a unique bundle name.
    gs_path = 'clone.bundle'
    if gs_subpath:
      gs_path = '%s/%s' % (gs_subpath, gs_path)

    # Path to the generated bundle file.
    bundle_path = self.bundle_dir.join('%s.bundle' % (self._hashname(gs_path),))

    # Create a new bundle.
    with self.m.context(cwd=git_path):
      self.m.git.bundle_create(bundle_path, name=s('create bundle'))

    # Upload the bundle to Google Storage.
    result = self.m.gsutil.upload(
        bundle_path,
        gs_bucket,
        gs_path,
        link_name='gsutil bundle',
        name=s('upload bundle'),
        unauthenticated_url=unauthenticated_url)
    return result.presentation.links['gsutil bundle']

  def create(self, git_path, gs_bucket, gs_subpath=None, name=None,
             unauthenticated_url=False):
    """
    Args:
      git_path: (Path) The path of the Git repository to bundle.
      gs_bucket: (str) The name of the Google Storage bucket.
      gs_subpath: (str) The path within the Google Storage bucket.
      name (str): If not None, the name of this bundle operation (to
          differentiate steps).
      unauthenticated_url: (bool) If True, request an unauthenticated URL from
          Google Storage.

    Returns: (str) The Google Storage URL where the bundle was uploaded.
    """
    self._setup()
    return self._bundle(git_path, gs_bucket, gs_subpath, name,
                        unauthenticated_url)

  def create_repo(self, repo_manifest_url, gs_bucket, gs_subpath=None,
                  remote_name=None, unauthenticated_url=False):
    """
    Traverses a 'repo' checkout and creates and uploads a Git bundle for each
    repository in the checkout.

    Args:
      repo_manifest_url: (str) The URL of the manifest to check out.
      gs_bucket: (str) The name of the Google Storage bucket.
      gs_subpath: (str) The path within the Google Storage bucket.
      remote_name: (str) If not None, the name of the remote to query. This is
          used to build the returned repository-to-GS mapping.
      unauthenticated_url: (bool) If True, request an unauthenticated URL from
          Google Storage.

    Returns: (dict) If 'remote_name' is supplied, a dictionary mapping the
        remote repository URL (key) to the Google Storage path (value) where
        that repository's bundle was uploaded.
    """
    self._setup()

    # Checkout the repository.
    checkout_root = self.base_path.join(
        'repo',
        hashlib.md5(repo_manifest_url).hexdigest())

    # Initialize the 'repo' checkout.
    self.m.file.ensure_directory('mkdir repo', checkout_root)
    with self.m.context(cwd=checkout_root):
      self.m.repo.init(repo_manifest_url)
      self.m.repo.sync('--no-clone-bundle')

    errors = []
    bundle_map = {}
    visited = set()
    with self.m.context(cwd=checkout_root):
      list_results = self.m.repo.list()
    for path, name in list_results:
      if name in visited:
        continue
      visited.add(name)
      repo_path = checkout_root.join(*path.split('/'))

      # Output to <gs_bucket>/[<gs_subpath>/]<path>
      gs_path = name
      if gs_subpath:
        gs_path = '%s/%s' % (gs_subpath, gs_path)
      try:
        upload_url = self._bundle(repo_path, gs_bucket, gs_path, name,
                                  unauthenticated_url)
        if remote_name:
          with self.m.context(cwd=repo_path):
            git_url = self.m.git.get_remote_url(
                name='lookup Git remote (%s)' % (name,),
                remote_name=remote_name)
          bundle_map[git_url] = upload_url
      except self.m.step.StepFailure as e:
        result = self.m.step.active_result
        result.presentation.step_text = 'Exception: %s' % (e,)
        result.presentation.status = self.m.step.FAILURE
        errors.append(e)

    if errors:
      raise self.m.step.StepFailure("Encountered %d bundler failure(s)" % (
          len(errors,)))
    return bundle_map

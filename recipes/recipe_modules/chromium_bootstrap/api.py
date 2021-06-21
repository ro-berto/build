# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class ChromiumBootstrapApi(recipe_api.RecipeApi):
  """Recipe module for modifying config with bootstrapped information.

  The bootstrapper communicates information about the bootstrapping
  process so that the recipe can operate in a manner that is consistent
  with the bootstrapping process (e.g. the bootstrapper communicates the
  gitiles commits accessed so that the recipe can sync code to the same
  version that the properties came from).
  """

  def __init__(self, input_properties, **kwargs):
    super(ChromiumBootstrapApi, self).__init__(**kwargs)
    self._commits = tuple(input_properties.commits)

  def update_gclient_config(self, gclient_config=None):
    """Update the gclient config to be consistent with the bootstrapper.

    This will update the revisions checked out by the gclient config so
    that for any files read by the bootstrapper, the same version should
    be checked out.
    """
    gclient_config = gclient_config or self.m.gclient.c
    for commit in self._commits:
      repo = 'https://{}/{}'.format(commit.host, commit.project)
      if repo not in gclient_config.repo_path_map:
        raise recipe_api.InfraFailure(
            'The bootstrapper checked out {repo}/+/{revision}, '
            'but the repo_path_map does not contain an entry for {repo}'.format(
                repo=repo, revision=commit.id))
      path, _ = gclient_config.repo_path_map[repo]
      gclient_config.revisions[path] = commit.id

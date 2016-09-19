# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to work with buildspec based GClient solutions."""

import config
import sys

from master.factory import gclient_factory
from master import gitiles_poller

def GetBuildspecSolution(buildspec, name=None, custom_deps_list=None,
                         managed=None):
  """Returns GClientSolution that can be used to checkout given buildspec.

  Args:
    buildspec: path to buildspec file relative to
        /chrome/tools/buildspec.git.
    name: Name for this solution.
    custom_deps_list: Modifications to make on the DEPS file.
    managed: Specify managed in .gclient file
  """
  url = (config.Master.git_internal_server_url +
                      '/chrome/tools/buildspec.git')
  return gclient_factory.GClientSolution(
      url,
      name,
      custom_deps_file=buildspec + '/DEPS',
      custom_deps_list=custom_deps_list,
      managed=managed
  )

def GetFileIsImportant(directory):
  """ Use FileIsImportant callable to watch changes in the
      given directory's buildspec DEPS files.

      Args:
        directory: the dir of the DEPS file
                   for example 'build/chrome-official'
  """
  def FileIsImportant(change):
    for fileChanged in change.files:
      if isinstance(directory, (list, tuple)):
        for d in directory:
          if fileChanged.startswith(d):
            return True
      elif fileChanged.startswith(directory):
        return True
    return False
  return FileIsImportant

class BuildspecPoller(gitiles_poller.GitilesPoller):
  def __init__(self, buildspec_prefixes, *args, **kwargs):
    self.buildspec_prefixes = buildspec_prefixes

    if kwargs['svn_mode']:
      kwargs.setdefault('repo_url', config.Master.git_internal_server_url +
                      '/chrome/tools/buildspec')
      kwargs.setdefault('revlinktmpl', 'https://uberchromegw.corp.google.com/'
                      'viewvc/chrome-internal?view=rev&revision=%s')
      kwargs.setdefault('svn_mode', True)
      kwargs['svn_branch'] = self.buildspec_svn_branch
    else:
      kwargs.setdefault('repo_url', config.Master.git_internal_server_url +
                      '/chrome/tools/buildspec.git')
      kwargs.setdefault('revlinktmpl', config.Master.git_internal_server_url +
                      '/chrome/tools/buildspec.git/+/%s')

    kwargs.setdefault('branches', ['master'])
    kwargs.setdefault('pollInterval', 30)

    kwargs['change_filter'] = self.buildspec_change_filter
    gitiles_poller.GitilesPoller.__init__(self, *args, **kwargs)

  def buildspec_svn_branch(self, commit_json, git_branch):
    for tree_entry in commit_json.get('tree_diff', []):
      for prefix in self.buildspec_prefixes:
        if tree_entry['new_path'].startswith(prefix):
          return prefix.rstrip('/').split('/')[-1]
    return git_branch.rpartition('/')[2]

  def buildspec_change_filter(self, commit_json, git_branch):
    if 'tree_diff' not in commit_json:
      return True
    for tree_entry in commit_json['tree_diff']:
      for prefix in self.buildspec_prefixes:
        if tree_entry['new_path'].startswith(prefix):
          return True
    return False

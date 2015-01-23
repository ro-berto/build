# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

import base64


class Gitiles(recipe_api.RecipeApi):
  """Module for polling a git repository using the Gitiles web interface."""
  def _curl(self, url, step_name):
    step_result = self.m.python(step_name,
      self.resource('gerrit_client.py'), [
      '--json-file', self.m.json.output(),
      '--url', url,
    ])

    return step_result

  def refs(self, url, step_name='refs'):
    """Returns a list of refs in the remote repository."""
    step_result = self._curl(
      self.m.url.join(url, '+refs?format=json'),
      step_name,
    )

    refs = sorted(str(ref) for ref in step_result.json.output)
    step_result.presentation.logs['refs'] = refs
    return refs

  def log(self, url, ref, num='all', step_name=None):
    """Returns the most recent commits under the given ref.

    Args:
      url: URL of the remote repository.
      ref: Name of the desired ref (see Gitiles.refs).
      num: Number of commits to limit the results to. Defaults to all.
      step_name: Custom name for this step. Will use the default if unspecified.

    Returns:
      A list of (commit hash, author) in reverse chronological order.
    """
    step_name = step_name or 'log: %s' % ref

    step_result = self._curl(
      self.m.url.join(url, '+log/%s?format=json&n=%s' % (ref, num)),
      step_name,
    )

    # The output is formatted as a JSON dict with a "log" key. The "log" key
    # is a list of commit dicts, which contain information about the commit.
    commits = [
      (str(commit['commit']), str(commit['author']['email']))
      for commit in step_result.json.output['log']
    ]

    step_result.presentation.logs['log'] = [commit[0] for commit in commits]
    step_result.presentation.step_text = '<br />%d new commits' % len(commits)
    return commits

  def download_file(self, repository_url, file_path, branch='master', **kwargs):
    """Downloads raw file content from a Gitiles repository.

    Args:
      repository_url: Full URL to the repository.
      file_path: Relative path to the file from the repository root.

    Returns:
      Raw file content.
    """
    kwargs.setdefault('step_name', 'Gitiles fetch %s' % file_path)
    full_url = '%s/+/%s/%s?format=text' % (repository_url.rstrip('/'), branch,
                                           file_path.lstrip('/'))
    b64_data = self.m.url.fetch(full_url, **kwargs)
    return base64.b64decode(b64_data)
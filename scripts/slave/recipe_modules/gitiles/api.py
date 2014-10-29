# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


class Gitiles(recipe_api.RecipeApi):
  """Module for polling a git repository using the Gitiles web interface."""
  def _curl(self, url, step_name):
    step_result = self.m.python(step_name,
      self.resource('gerrit_client.py'), [
      '--json-file', self.m.json.output(add_json_log=False),
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

    for ref in refs:
      step_result.presentation.links[ref] = self.m.url.join(url, '+', ref)

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

    for commit in commits:
      step_result.presentation.links[commit[0]] = self.m.url.join(
        url, '+', commit[0]
      )

    return commits

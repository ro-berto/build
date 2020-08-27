# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

import re


class CrrevApi(recipe_api.RecipeApi):
  """Recipe module for making requests to crrev.com."""

  def __call__(self, step_name, request_path, request_params=None, attempts=3,
               **kwargs):
    step_result = self.m.build.python(
        step_name,
        self.resource('crrev_client.py'),
        [
            request_path,
            '--params-file', self.m.json.input(request_params or {}),
            '--attempts', str(attempts),
        ],
        show_path=False, # Can't dump path, since we use STDOUT.
        stdout=self.m.json.output(),
        **kwargs)
    return step_result.stdout

  def to_commit_hash(
      self, commit_position, project='chromium', repo='chromium/src',
      attempts=3, step_name=None, **kwargs):
    """Fetches the corresponding commit hash for a commit position."""
    ref, number = self.m.commit_position.parse(commit_position)
    params = {
        'numbering_type': 'COMMIT_POSITION',
        'numbering_identifier': ref,
        'number': number,
        'project': project,
        'repo': repo,
    }
    step_name = step_name or 'crrev get commit hash for ' + commit_position
    try:
      result = self(step_name, 'get_numbering', params, attempts, **kwargs)
      return result['git_sha']
    except (self.m.step.StepFailure, KeyError):
      raise self.m.step.StepFailure('Could not resolve ' + commit_position)

  def to_commit_position(self, commit_hash, attempts=3, step_name=None):
    """Fetches a commit position string given a commit hash."""
    if not re.match(r'^[0-9a-zA-Z]{40}$', commit_hash):
      raise ValueError('Not a full 40-digit SHA1 hash (%s)' % commit_hash)
    step_name = step_name or 'crrev get commit position for ' + commit_hash
    try:
      result = self(step_name, 'commit_path/' + commit_hash, attempts=attempts)
      numberings = result['numberings']
    except (self.m.step.StepFailure, KeyError):
      raise self.m.step.StepFailure('Could not resolve ' + commit_hash)
    for numbering in numberings:
      if numbering['numbering_type'] == 'COMMIT_POSITION':
        ref = numbering['numbering_identifier']
        number = numbering['number']
        return self.m.commit_position.format(ref, number)
    raise self.m.step.StepFailure('No commit position for ' + commit_hash)

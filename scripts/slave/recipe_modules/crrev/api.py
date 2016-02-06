# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class CrrevApi(recipe_api.RecipeApi):
  """Recipe module for making requests to crrev.com."""

  def chromium_hash_from_commit_position(self, commit_pos):
    """Resolve a commit position in the chromium repo to its commit hash."""
    try:
      int_pos = int(commit_pos)
    except (ValueError, TypeError):
      raise self.m.step.StepFailure('Invalid commit position (%s).'
                                    % (commit_pos,))
    try:
      step_result = self.m.python(
          'resolving commit_pos ' + str(commit_pos),
          self.resource('crrev.py'),
          ['commit_hash', commit_pos],
          stdout=self.m.raw_io.output())
    except self.m.step.StepFailure:  # pragma: no cover
      raise self.m.step.StepFailure(
          'Could not get commit hash for commit position: ' + str(commit_pos))
    return step_result.stdout

  def chromium_commit_position_from_hash(self, sha):
    """Resolve a chromium commit hash to its commit position."""
    try:
      assert int(sha, 16)
      sha = str(sha)  # Unicode would break the step when passed in the name
    except (AssertionError, ValueError, TypeError):
      raise self.m.step.StepFailure('Invalid commit hash: ' + sha)

    try:
      step_result = self.m.python(
          'resolving hash ' + sha,
          self.resource('crrev.py'),
          ['commit_hash', sha],
          stdout=self.m.raw_io.output())
      result = int(step_result.stdout)
    except (self.m.step.StepFailure, ValueError, TypeError):
      raise self.m.step.StepFailure(
          'Could not fetch commit position for hash: ' + sha)
    return result


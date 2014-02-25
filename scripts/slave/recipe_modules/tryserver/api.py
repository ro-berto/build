# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from slave import recipe_api


class TryserverApi(recipe_api.RecipeApi):
  @property
  def is_tryserver(self):
    """Returns true iff we can apply_issue or patch."""
    return self.can_apply_issue or self.can_patch

  @property
  def can_apply_issue(self):
    """Returns true iff the properties exist to apply_issue from rietveld."""
    return (self.m.properties.get('rietveld')
            and 'issue' in self.m.properties
            and 'patchset' in self.m.properties)

  @property
  def can_patch(self):
    """Returns true iff the properties exist to patch from a patch URL."""
    return self.m.properties.get('patch_url')

  def maybe_apply_issue(self, cwd=None):
    """If we're a trybot, apply a codereview issue.

    cwd: If specified, apply the patch from the specified directory.
    """
    if self.can_patch:
      def link_patch(step_result):
        """Links the patch.diff file on the waterfall."""
        step_result.presentation.logs['patch.diff'] = (
          step_result.raw_io.output.split('\n'))

      svn_cmd = [
        'svn',
        'export',
        '--force',
        self.m.properties['patch_url'],
        self.m.raw_io.output('.diff'),
      ]

      yield self.m.step('download patch', svn_cmd, followup_fn=link_patch,
                        step_test_data=self.test_api.download_patch)

      patch_content = self.m.raw_io.input(
        self.m.step_history.last_step().raw_io.output)

      patch_cmd = [
        'patch',
        '--dir', cwd or self.m.path.checkout(),
        '--force',
        '--forward',
        '--input', patch_content,
        '--remove-empty-files',
        '--strip', '0',
      ]

      yield self.m.step('apply patch', patch_cmd)
    elif self.can_apply_issue:
      yield self.m.rietveld.apply_issue(self.m.rietveld.calculate_issue_root())

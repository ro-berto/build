# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


class PresubmitApi(recipe_api.RecipeApi):
  """PresubmitApi provides common functionality to run presubmit tests."""

  def commit_patch_locally(self, root=''):
    """Commit patch locally after it has been applied in bot_update.

    This is needed by infra repositories, since presubmit expects no uncommitted
    changes.
    """
    # TODO(hinoka): Extract email/name from issue?
    self.m.git('-c', 'user.email=commit-bot@chromium.org',
               '-c', 'user.name=The Commit Bot',
               'commit', '-a', '-m', 'Committed patch',
               name='commit git patch',
               cwd=self.m.path['checkout'].join(root))

  def __call__(self, root='', upstream='', trybot_json_output=None,
               use_rietveld_credentials=False):
    """Runs presubmit.

    Args:
      root: Search for PRESUBMIT.py up to this directory.
      upstream: Git only: the base ref or upstream branch against which the diff
          should be computed.
    """
    presubmit_args = [
      '--root', self.m.path['checkout'].join(root),
      '--commit',
      '--verbose', '--verbose',
      '--issue', self.m.properties['issue'],
      '--patchset', self.m.properties['patchset'],
      '--skip_canned', 'CheckRietveldTryJobExecution',
      '--skip_canned', 'CheckTreeIsOpen',
      '--skip_canned', 'CheckBuildbotPendingBuilds',
      '--rietveld_url', self.m.properties['rietveld'],
      '--rietveld_fetch',
      '--upstream', upstream,  # '' if not in bot_update mode.
    ]

    if trybot_json_output:
      presubmit_args.extend(['--trybot-json', trybot_json_output])

    if use_rietveld_credentials:
      presubmit_args.extend([
          '--rietveld_email_file',
          self.m.path['build'].join('site_config', '.rietveld_client_email')])
      presubmit_args.extend([
          '--rietveld_private_key_file',
          self.m.path['build'].join('site_config', '.rietveld_secret_key')])
    else:
      presubmit_args.extend(['--rietveld_email', ''])  # activate anonymous mode

    self.m.python(
        'presubmit', self.m.path['depot_tools'].join('presubmit_support.py'),
        presubmit_args)
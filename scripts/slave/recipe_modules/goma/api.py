# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

class GomaApi(recipe_api.RecipeApi):
  """GomaApi contains helper functions for using goma."""

  @property
  def service_account_json_path(self):
    if self.m.platform.is_win:
      return 'C:\\creds\\service_accounts\\service-account-goma-client.json'
    return '/creds/service_accounts/service-account-goma-client.json'

  def update_goma_canary(self):
    """Returns a step for updating goma canary."""
    # deprecated? switch to use ensure_goma with canary=True.
    # for git checkout, should use @refs/heads/master to use head.
    head = 'refs/heads/master'
    # TODO(phajdan.jr): Remove path['build'] usage, http://crbug.com/437264 .
    self.m.gclient('update goma canary',
                   ['sync', '--verbose', '--force',
                    '--revision', 'build/goma@%s' % head],
                   cwd=self.m.path['build'])

  def ensure_goma(self):
    with self.m.step.nest('ensure_goma'):
      try:
        self.m.cipd.set_service_account_credentials(
            self.service_account_json_path)

        self.m.cipd.install_client()
        goma_package = ('infra_internal/goma/client/%s' %
            self.m.cipd.platform_suffix())
        goma_dir = self.m.path['cache'].join('cipd', 'goma')
        self.m.cipd.ensure(goma_dir, {goma_package: 'release'})
        return goma_dir
      except self.m.step.StepFailure:  # pragma: no cover
        # TODO(phajdan.jr): make failures fatal after experiment.
        return None

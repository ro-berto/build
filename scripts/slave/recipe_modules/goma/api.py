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

  def ensure_goma(self, canary=False):
    with self.m.step.nest('ensure_goma'):
      try:
        self.m.cipd.set_service_account_credentials(
            self.service_account_json_path)

        self.m.cipd.install_client()
        goma_package = ('infra_internal/goma/client/%s' %
            self.m.cipd.platform_suffix())
        # For Windows there's only 64-bit goma client.
        if self.m.platform.is_win:
          goma_package = goma_package.replace('386', 'amd64')
        ref='release'
        if canary:
          ref='candidate'
        goma_dir = self.m.path['cache'].join('cipd', 'goma')
        self.m.cipd.ensure(goma_dir, {goma_package: ref})
        return goma_dir
      except self.m.step.StepFailure:  # pragma: no cover
        # TODO(phajdan.jr): make failures fatal after experiment.
        return None

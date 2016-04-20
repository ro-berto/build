# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

class GomaApi(recipe_api.RecipeApi):
  """GomaApi contains helper functions for using goma."""

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

  def ensure_goma(self, goma_dir, canary=False, pure_cipd=False):
    # TODO(iannucci): switch to CIPD (https://goto.google.com/toxxq).
    with self.m.step.nest('ensure_goma'):
      try:
        # TODO(phajdan.jr): remove "no cover" after enabling on Windows.
        if self.m.platform.is_win:  # pragma: no cover
          creds = ('C:\\creds\\service_accounts\\'
                   'service-account-goma-client.json')
        else:
          creds = '/creds/service_accounts/service-account-goma-client.json'
        self.m.cipd.set_service_account_credentials(creds)

        self.m.cipd.install_client()
        goma_package = ('infra_internal/goma/client/%s' %
            self.m.cipd.platform_suffix())
        self.m.cipd.ensure(
            self.m.path['cache'].join('cipd', 'goma'),
            {goma_package: 'latest'})
      except self.m.step.StepFailure:  # pragma: no cover
        # TODO(phajdan.jr): make failures fatal after experiment.
        pass

      if pure_cipd:
        return

      args=[
          '--target-dir', goma_dir,
          '--download-from-google-storage-path',
          self.m.depot_tools.download_from_google_storage_path
      ]
      if canary:
        args += ['--canary']
      self.m.python(
        name='ensure_goma',
        script=self.resource('ensure_goma.py'),
        args=args,
        infra_step=True)

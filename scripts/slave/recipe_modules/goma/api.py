# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

class GomaApi(recipe_api.RecipeApi):
  """GomaApi contains helper functions for using goma."""

  def update_goma_canary(self):
    """Returns a step for updating goma canary."""
    # for git checkout, should use @refs/heads/master to use head.
    head = 'refs/heads/master'
    # TODO(phajdan.jr): Remove path['build'] usage, http://crbug.com/437264 .
    self.m.gclient('update goma canary',
                   ['sync', '--verbose', '--force',
                    '--revision', 'build/goma@%s' % head],
                   cwd=self.m.path['build'])

  def ensure_goma(self, goma_dir):
    # TODO(iannucci): switch to CIPD (https://goto.google.com/toxxq).
    self.m.python(
      name='ensure_goma',
      script=self.resource('ensure_goma.py'),
      args=[
        '--target-dir', goma_dir,
        '--download-from-google-storage-path',
        self.m.depot_tools.download_from_google_storage_path
      ],
      infra_step=True)

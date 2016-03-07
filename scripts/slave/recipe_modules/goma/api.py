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
    self.m.gclient('update goma canary',
                   ['sync', '--verbose', '--force',
                    '--revision', 'build/goma@%s' % head],
                   cwd=self.m.path['build'])

  def ensure_goma(self):
    # Return early if goma is configured off for this build.
    if (not self.m.chromium.c.compile_py.compiler or
        'goma' not in self.m.chromium.c.compile_py.compiler):
      return

    # New code is only enabled on whitelisted platforms for now.
    # Other platforms continue to use DEPS-ed goma.
    if not self.m.platform.is_linux:
      return

    goma_dir = self.m.path['checkout'].join('build', 'goma', 'client')

    self.m.chromium.c.gyp_env.GYP_DEFINES['gomadir'] = goma_dir
    self.m.chromium.c.compile_py.goma_dir = goma_dir

    # TODO(iannucci): switch to CIPD (https://goto.google.com/toxxq).
    self.m.python(
      name='ensure_goma',
      script=self.resource('ensure_goma.py'),
      args=[
        '--target-dir', goma_dir,
      ],
      infra_step=True)

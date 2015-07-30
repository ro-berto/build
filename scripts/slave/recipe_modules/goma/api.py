# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

class GomaApi(recipe_api.RecipeApi):
  """GomaApi contains helper functions for using goma."""

  def update_goma_canary(self, buildername):
    """Returns a step for updating goma canary."""
    head = 'HEAD'
    # git checkout doesn't work with @HEAD, but @refs/heads/master
    # As of July 29, Mac goma canaries are git checkout, others are not.
    if 'Mac' in buildername:
      head = 'refs/heads/master'
    self.m.gclient('update goma canary',
                   ['sync', '--verbose', '--force',
                    '--revision', 'build/goma@%s' % head],
                   cwd=self.m.path['build'])

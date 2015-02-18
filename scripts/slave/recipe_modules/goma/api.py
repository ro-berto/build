# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


class GomaApi(recipe_api.RecipeApi):
  """GomaApi contains helper functions for using goma."""

  def diagnose_goma(self):
    """Returns a step for checking goma log."""
    self.m.python('diagnose_goma',
                  self.m.path['build'].join('goma', 'diagnose_goma_log.py'))

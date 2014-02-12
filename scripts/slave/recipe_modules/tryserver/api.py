# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from slave import recipe_api


class TryserverApi(recipe_api.RecipeApi):

  @property
  def is_tryserver(self):
    """Determine whether we're a trybot.

    Checks for the presence of the "rietveld" property or a specified patch_url.
    """
    return 'rietveld' in self.m.properties or self.m.properties.get('patch_url')

  def maybe_apply_issue(self):
    """If we're a trybot, apply a codereview issue."""
    if self.is_tryserver:
      # TODO(iannucci,phajdan): Make this fall back to patch application from
      # 'patch_url'
      yield self.m.rietveld.apply_issue(self.m.rietveld.calculate_issue_root())

# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class RietveldApi(recipe_api.RecipeApi):
  def apply_issue(self, *root_pieces):
    return self.m.step('apply_issue', [
        self.m.path.depot_tools('apply_issue'),
        '-r', self.m.path.checkout(*root_pieces),
        '-i', self.m.properties['issue'],
        '-p', self.m.properties['patchset'],
        '-s', self.m.properties['rietveld'],
        '-e', 'commit-bot@chromium.org'])


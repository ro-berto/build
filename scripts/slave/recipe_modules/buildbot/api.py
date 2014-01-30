# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class BuildbotApi(recipe_api.RecipeApi):
  def prep(self):
    """Prepatory steps for buildbot based recipes."""
    # TODO(iannucci): Also do taskkill?
    return self.m.python(
      'cleanup temp',
      self.m.path.build('scripts', 'slave', 'cleanup_temp.py')
    )

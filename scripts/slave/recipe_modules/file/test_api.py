# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class FileTestApi(recipe_test_api.RecipeTestApi):
  def listdir(self, dirname, files):
    return self.step_data(
      'listdir %s' % dirname,
      self.m.json.output(files))


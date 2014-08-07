# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class ChromiumTestsApi(recipe_api.RecipeApi):
  def setup_chromium_tests(self, test_runner):
    if self.m.platform.is_win:
      self.m.chromium.crash_handler()

    ret = test_runner()

    if self.m.platform.is_win:
      self.m.chromium.process_dumps()

    return ret

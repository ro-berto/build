# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class ChromiumTestsApi(recipe_api.RecipeApi):
  def setup_chromium_tests(self, test_runner):
    if self.m.chromium.c.TARGET_PLATFORM == 'android':
      self.m.chromium_android.common_tests_setup_steps()

    if self.m.platform.is_win:
      self.m.chromium.crash_handler()

    try:
      return test_runner()
    finally:
      if self.m.platform.is_win:
        self.m.chromium.process_dumps()

      if self.m.chromium.c.TARGET_PLATFORM == 'android':
        self.m.chromium_android.common_tests_final_steps()

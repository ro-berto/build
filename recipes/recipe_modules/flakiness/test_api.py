# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class FlakinessTestApi(recipe_test_api.RecipeTestApi):

  def __call__(self, identify_new_tests=False):
    return self.m.properties(
        **{'$build/flakiness': {
            'identify_new_tests': identify_new_tests
        }})

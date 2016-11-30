# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from copy import deepcopy
from recipe_engine import recipe_test_api

class iOSTestApi(recipe_test_api.RecipeTestApi):
  @recipe_test_api.mod_test_data
  @staticmethod
  def build_config(config):
    return deepcopy(config)

  def make_test_build_config(self, config):
    return self.build_config(config)

  @recipe_test_api.mod_test_data
  @staticmethod
  def parent_build_config(config):
    return deepcopy(config)

  def make_test_build_config_for_parent(self, config):
    return self.parent_build_config(config)

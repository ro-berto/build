# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from PB.infra.chromium import chromium_bootstrap


class ChromiumBootstrapApi(recipe_test_api.RecipeTestApi):

  def properties(self, commits):
    return self.m.properties(
        **{
            '$build/chromium_bootstrap':
                chromium_bootstrap.ChromiumBootstrapModuleProperties(
                    commits=commits)
        })

# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Exposes the builder and recipe configurations to GenTests in recipes.

from recipe_engine import recipe_test_api
from . import builders


class LibyuvTestApi(recipe_test_api.RecipeTestApi):
  BUILDERS = builders.BUILDERS
  RECIPE_CONFIGS = builders.RECIPE_CONFIGS

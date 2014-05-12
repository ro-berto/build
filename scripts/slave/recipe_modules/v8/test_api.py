# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Exposes the builder and recipe configurations to GenTests in recipes.

from slave import recipe_test_api
from slave.recipe_modules.v8 import builders


class V8TestApi(recipe_test_api.RecipeTestApi):
  BUILDERS = builders.BUILDERS

# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Exposes the builder and recipe configurations to GenTests in recipes.

import base64

from recipe_engine import recipe_test_api
from . import builders
from . import steps


class WebRTCTestApi(recipe_test_api.RecipeTestApi):
  BUILDERS = builders.BUILDERS
  RECIPE_CONFIGS = builders.RECIPE_CONFIGS
  NORMAL_TESTS = steps.NORMAL_TESTS

  def example_binary_sizes(self):
    return self.m.json.output({'some_binary': 123456})

  def example_patch(self):
    return self.m.json.output({
        'value': base64.b64encode('diff --git a/a b/a\nnew file mode 100644\n')
    })

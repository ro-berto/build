# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api

from RECIPE_MODULES.build.chromium_tests_builder_config import (builder_db,
                                                                try_spec)


class ANGLETestsApi(recipe_test_api.RecipeTestApi):

  @recipe_test_api.mod_test_data
  @staticmethod
  def builders(builders):
    """Override test builders for a test.

    Args:
      builders - A BuilderDatabase to replace angle.builders.
    """
    assert isinstance(builders, builder_db.BuilderDatabase)
    return builders

  @recipe_test_api.mod_test_data
  @staticmethod
  def trybots(trybots):
    """Override test builders for a test.

    Args:
      trybots - A TryDatabase to replace angle.trybots.
    """
    assert isinstance(trybots, try_spec.TryDatabase)
    return trybots

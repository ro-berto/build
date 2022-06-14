# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class FlakyReproducerTestApi(recipe_test_api.RecipeTestApi):

  def __init__(self, *args, **kwargs):
    super(FlakyReproducerTestApi, self).__init__(*args, **kwargs)

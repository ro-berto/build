# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class UrlApi(recipe_api.RecipeApi):
  def join(self, *parts):
    return '/'.join(str(x).strip('/') for x in parts)

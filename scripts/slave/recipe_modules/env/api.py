# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
from slave import recipe_api

class Env(recipe_api.RecipeApi):
  """A wrapper for a read-only view of os.environ."""
  def __init__(self, *args, **kwargs):
    super(Env, self).__init__(*args, **kwargs)

  def get(self, key, default=None):
    ret = os.environ.get(key, default)
    if self._test_data.enabled:
      ret = self._test_data.get('test_environ', {}).get(key, default)
    return ret

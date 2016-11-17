# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

class ToolsBuildApi(recipe_api.RecipeApi):

  @property
  def slave_utils_args(self):
    """Returns (list): A list of arguments to supply to configure slave_utils
        parameters. See `slave_utils.py`'s AddArgs method.
    """
    return [
        '--slave-utils-gsutil-py-path', self.m.depot_tools.gsutil_py_path,
    ]

# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

class ToolsBuildApi(recipe_api.RecipeApi):

  @property
  def slave_utils_args(self):
    """Returns (list): A list of arguments to supply to configure slave_utils
        parameters. See `slave_utils.py`'s AddArgs method.

    TODO(dnj): This function and its invocations should be deprecated in favor
    of using environment variables via "add_slave_utils_kwargs". The script
    invocation path for some of these is just too intertwined to confidently
    apply this via explicit args everywhere.
    """
    return [
        '--slave-utils-gsutil-py-path', self.m.depot_tools.gsutil_py_path,
    ]

  def add_slave_utils_kwargs(self, kwargs):
    """Augments step/python keyword arguments with `slave_utils.py` parameters.
    """
    env = kwargs.setdefault('env', {})
    env['BUILD_SLAVE_UTILS_GSUTIL_PY_PATH'] = self.m.depot_tools.gsutil_py_path
    return kwargs

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

import os
import re
import traceback


class TracebackApi(recipe_api.RecipeApi):

  def _regex_safe_path_join(self, *args):
    if self.m.path.sep == '\\':
      sep = '\\\\'
    else:
      sep = self.m.path.sep
    return sep.join(args)

  def format_exc(self):
    """Returns a string containing an exception traceback.

    Calls traceback.format_exc but during testing removes absolute paths.
    """
    s = traceback.format_exc()
    if self._test_data.enabled:
      # Make the traceback appear in "native" format by replacing the path
      # separators.
      s = s.replace(os.path.sep, self.m.path.sep)

      # traceback.format_exc output includes path to source files. This makes
      # the output dependent on the location where the source code is checked
      # out too. For testing we want the output to be location independent.
      s = re.sub(
          self._regex_safe_path_join('File "[^"]*', '\\.recipe_deps', ''),
          self._regex_safe_path_join('File "<...>', ''),
          s)
      s = re.sub(
          self._regex_safe_path_join('File "[^"]*', 'infra', ''),
          self._regex_safe_path_join('File "<...>', 'infra', ''),
          s)
      s = re.sub(
          self._regex_safe_path_join('File "[^"]*', 'recipe_modules', ''),
          self._regex_safe_path_join('File "<...>', 'recipe_modules', ''),
          s)
      s = re.sub(
          self._regex_safe_path_join('File "[^"]*', 'recipe_engine', ''),
          self._regex_safe_path_join('File "<...>', 'recipe_engine', ''),
          s)
      s = re.sub(
          self._regex_safe_path_join('File "[^"]*', 'python[23].[0-9]', ''),
          self._regex_safe_path_join('File "<...>', 'pythonX.X', ''),
          s)
    return s

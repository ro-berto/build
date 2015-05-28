# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
BUILD_INTERNAL_ROOT = os.path.join(
    os.path.dirname(BUILD_ROOT), 'build_internal')

sys.path.append(os.path.join(BUILD_ROOT, 'third_party'))

_UNIVERSE = None
def get_universe():
  from recipe_engine import loader
  global _UNIVERSE
  if _UNIVERSE is None:
    roots = [BUILD_ROOT, BUILD_INTERNAL_ROOT]
    _UNIVERSE = loader.RecipeUniverse(
        module_dirs=[ os.path.join(root, 'scripts', 'slave', 'recipe_modules')
                      for root in roots ],
        recipe_dirs=[ os.path.join(root, 'scripts', 'slave', 'recipes')
                      for root in roots ])
  return _UNIVERSE


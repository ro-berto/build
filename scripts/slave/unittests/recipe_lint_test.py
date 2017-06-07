#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

MODULES_WHITELIST = [
  # TODO(martiniss): Move skia modules into recipe resources
  r'common\.skia\..*',
  r'slave\.skia\..*',
  r'slave\.recipe_modules\.swarming\.resources\..*'
]

RECIPES_PY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    'recipes.py')

args = [sys.argv[0], 'lint']
for pattern in MODULES_WHITELIST:
  args.extend(['-w', pattern])
os.execvp(RECIPES_PY, args)


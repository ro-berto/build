#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

import test_env  # pylint: disable=W0403,W0611

from recipe_engine import lint_test
from slave import recipe_universe

MODULES_WHITELIST = [
  # TODO(luqui): Move skia modules into recipe resources
  r'common\.skia\..*',
  r'slave\.skia\..*',

  # TODO(luqui): Move cros modules into recipe resources
  r'common\.cros_chromite',
]

if __name__ == '__main__':
  lint_test.main(recipe_universe.get_universe(), whitelist=MODULES_WHITELIST)

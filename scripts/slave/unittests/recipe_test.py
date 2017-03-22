#!/usr/bin/env python
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import pipes
import shutil
import subprocess
import sys

RECIPES_PY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    'recipes.py')

args = [
  RECIPES_PY,
  "--use-bootstrap",
]

if 'CHROME_HEADLESS' in os.environ:
  args += ["--deps-path=-"]

args += [
    'test', 'run'
]
sys.exit(subprocess.call(args))

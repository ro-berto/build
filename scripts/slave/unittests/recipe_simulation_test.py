#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import pipes
import shutil
import subprocess
import sys

import test_env  # pylint: disable=W0403,W0611

# Load our ".recipe_deps" tag name from the environment.
recipe_deps_tag = os.environ.get('RECIPE_SIMULATION_TEST_DEPS_TAG')

# Delete the old recipe_engine directory which might have stale pyc files
# that will mess us up.
shutil.rmtree(os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__))))),
        'third_party', 'recipe_engine'),
    ignore_errors=True)

RECIPES_PY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    'recipes.py')

args = [RECIPES_PY]
if recipe_deps_tag:
  args += ['--deps-path', os.path.join(os.getcwd(), '.%s_recipe_deps' % (
      recipe_deps_tag,))]
args += ['simulation_test'] + sys.argv[1:]
ret = subprocess.call(args)
if ret:
  # TODO(martiniss): Move this logic into recipes-py. http://crbug.com/601662
  if not any(x.startswith('train') for x in args):
    print
    print 'To train new expectations, run:'
    print '   ', sys.argv[0], 'train'
    print
  if not any(x.startswith('--html_report') for x in args):
    print 'To create a coverage report, run:'
    print '   ', ' '.join(pipes.quote(arg) for arg in sys.argv),
    print '--html_report PATH'
    print
sys.exit(ret)

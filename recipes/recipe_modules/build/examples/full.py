# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.build.chromium_tests.steps import ResultDB

DEPS = [
    'build',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/raw_io',
]


def RunSteps(api):
  assert api.build.bot_utils_args

  api.build.python(
      'vpython with resultdb',
      'foo.py',
      args=['--foo', '--bar'],
      venv=api.path['cache'].join('path', 'to', 'venv'),
      resultdb=ResultDB.create(enable=True),
  )


def GenTests(api):
  yield api.test('basic', api.buildbucket.try_build())

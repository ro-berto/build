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
  assert api.build.slave_utils_args

  with api.build.gsutil_py_env():
    api.build.python('runtest', 'foo.py', args=['--foo', '--bar'])

  api.build.python(
      'unbuffered vpython',
      'foo.py',
      unbuffered=False,
      venv=api.path['cache'].join('path', 'to', 'venv'),
  )

  api.build.python(
      'legacy annotation',
      'foo.py',
      legacy_annotation=True,
  )

  api.build.python(
      'vpython with resultdb',
      'foo.py',
      venv=api.path['cache'].join('path', 'to', 'venv'),
      resultdb=ResultDB.create(enable=True),
  )

  api.build.python(
      'legacy with resultdb',
      'foo.py',
      legacy_annotation=True,
      resultdb=ResultDB.create(enable=True),
  )


def GenTests(api):
  yield api.test('basic', api.buildbucket.try_build())

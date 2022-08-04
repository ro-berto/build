# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.build.chromium_tests import resultdb

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]

PROPERTIES = {
    'env': Property(kind=dict, default=None),
    'resultdb': Property(kind=resultdb.ResultDB, default=None),
}


def RunSteps(api, env, resultdb):
  api.isolate.run_isolated(
      'run_isolated',
      'isolate_hash',
      ['some', 'args'],
      env=env,
      resultdb=resultdb,
  )


def GenTests(api):
  yield api.test('basic')

  yield api.test(
      'env',
      api.properties(env={'VAR': 'value'}),
      api.post_check(lambda check, steps: \
        check(['--env', 'VAR=value'] in steps['run_isolated'].cmd)),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'rdb',
      api.properties(resultdb=resultdb.ResultDB.create()),
      # Create a buildbucket build so that the luci context is initialized with
      # resultdb
      api.buildbucket.generic_build(),
      # TODO(gbeaty) Replace Ellipsis with ... once we have python3 syntax
      # available
      api.post_check(lambda check, steps: \
        check(['rdb', 'stream', Ellipsis, '--', 'python']
              in steps['run_isolated'].cmd)),
      api.post_process(post_process.DropExpectation),
  )

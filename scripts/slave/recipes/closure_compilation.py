# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'depot_tools/gclient',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]


MASTERS = freeze({
  'chromium.fyi': {
    'buildername': 'Closure Compilation Linux',
    'testname': 'closure_compilation_fyi',
  },
  'tryserver.chromium.linux': {
    'buildername': 'closure_compilation',
    'testname': 'closure_compilation_try',
  },
})


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('ninja')

  api.bot_update.ensure_checkout()

  api.python(
      'run_tests',
      api.path['checkout'].join('third_party', 'closure_compiler',
                                'run_tests.py')
  )

  api.step(
      'generate_gyp_files',
      [api.path['checkout'].join('build', 'gyp_chromium'),
       api.path['checkout'].join('third_party', 'closure_compiler',
                                 'compiled_resources2.gyp')],
  )

  api.chromium.compile()


def GenTests(api):
  for mastername, config in MASTERS.iteritems():
    yield (
      api.test(config['testname']) +
      api.properties.generic(
          buildername=config['buildername'],
          mastername=mastername,
      )
    )

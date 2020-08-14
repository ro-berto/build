# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
    'builder_group',
    'chromium',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]

BUILDER_GROUPS = freeze({
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


def GenTests(api):
  for group, config in BUILDER_GROUPS.iteritems():
    yield api.test(
        config['testname'],
        api.builder_group.for_current(group),
        api.properties(buildername=config['buildername']),
    )

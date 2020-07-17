# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'test_utils',
]


def RunSteps(api):
  assert api.tryserver.is_tryserver
  raw_result = api.chromium_tests.trybot_steps()
  return raw_result


def GenTests(api):
  yield api.test(
      'analyze deps autorolls',
      api.chromium.try_build(),
      api.override_step_data(
          'gerrit fetch current CL info',
          api.json.output([{
              'owner': {
                  # chromium-autoroller
                  '_account_id': 1302611
              },
              'branch': 'master',
              'revisions': {},
          }])),
      api.override_step_data('git diff to analyze patch',
                             api.raw_io.stream_output('DEPS')),
  )

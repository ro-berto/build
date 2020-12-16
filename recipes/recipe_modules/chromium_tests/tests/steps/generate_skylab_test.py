# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'builder_group',
    'chromium',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/step',
    'skylab',
    'test_results',
    'test_utils',
]

from RECIPE_MODULES.build.chromium_tests import generators


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')
  api.test_results.set_config('public_server')

  update_step = api.bot_update.ensure_checkout()

  source_side_spec = {
      'test_buildername': {
          'skylab_tests': [{
              "cros_board": "eve",
              "cros_img": "eve-release/R89-13631.0.0",
              "name": "basic_EVE_TOT",
              "suite": "lacros-basic",
              "swarming": {},
              "test": "basic",
              "timeout": 3600
          }, {
              "cros_board": "eve",
              "cros_img": "eve-release/R88-13597.15.0",
              "name": "basic_EVE_TOT-1",
              "suite": "lacros-basic",
              "swarming": {},
              "test": "basic",
              "timeout": 3600
          }],
      }
  }

  for test_spec in generators.generate_skylab_tests(api, api.chromium_tests,
                                                    'test_group',
                                                    'test_buildername',
                                                    source_side_spec,
                                                    update_step):
    test = test_spec.get_test()
    test.pre_run(api, '')
    test.run(api, '')


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
  )

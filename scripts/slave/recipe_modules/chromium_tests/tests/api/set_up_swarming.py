# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium_swarming',
    'chromium_tests',
    'isolate',
    'recipe_engine/assertions',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/runtime',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium.types import BuilderId


def RunSteps(api):
  bot_config = api.chromium_tests.create_bot_config_object(
      [BuilderId.create_for_master('test_mastername', 'test_buildername')],
      builders={
          'test_mastername': {
              'builders': {
                  'test_buildername': {
                      'isolate_server': 'https://example/isolate',
                      'swarming_server': 'https://example/swarming',
                      'swarming_dimensions': {
                          'os': 'Ubuntu-14.04'
                      },
                  },
              },
          },
      })

  api.chromium_tests.set_up_swarming(bot_config)
  api.assertions.assertEqual(api.chromium_swarming.swarming_server,
                             api.properties.get('expected_swarming_server'))
  api.assertions.assertEqual(
      api.chromium_swarming.service_account_json,
      api.properties.get('expected_swarming_service_account'))
  api.assertions.assertEqual(api.chromium_swarming.default_dimensions,
                             api.properties.get('expected_swarming_dimensions'))
  api.assertions.assertEqual(api.isolate.isolate_server,
                             api.properties.get('expected_isolate_server'))
  api.assertions.assertEqual(
      api.isolate.service_account_json,
      api.properties.get('expected_isolate_service_account'))


def GenTests(api):
  yield api.test(
      'luci',
      api.platform.name('linux'),
      api.properties(
          expected_swarming_server='https://example/swarming',
          expected_swarming_service_account=None,
          expected_swarming_dimensions={
              'cpu': 'x86-64',
              'gpu': None,
              'os': 'Ubuntu-14.04',
          },
          expected_isolate_server='https://example/isolate',
          expected_isolate_service_account=None),
      api.runtime(is_luci=True, is_experimental=False),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

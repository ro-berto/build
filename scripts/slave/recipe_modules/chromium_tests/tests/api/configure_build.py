# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy
from recipe_engine import post_process


DEPS = [
    'chromium_tests',
    'recipe_engine/platform',
    'recipe_engine/properties',
]

BASIC_CONFIG = {
  'android_config': 'main_builder_mb',
  'chromium_config': 'chromium',
  'gclient_config': 'chromium',
  'test_results_config': 'public_server',
}


BUILDERS = {
  'fake.master': {
    'builders': {
      'Android Apply Config Builder': dict(BASIC_CONFIG, **{
        'android_apply_config': [
          'use_devil_provision',
        ],
      }),
      'Chromium Tests Apply Config Builder': dict(BASIC_CONFIG, **{
        'chromium_tests_apply_config': [
          'staging',
        ],
      }),
      'Component Rev Builder': dict(BASIC_CONFIG, **{
        'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
      }),
    },
  },
}


def RunSteps(api):
  bot_config_object = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(
          api.properties['mastername'], api.properties['buildername'])],
      builders=BUILDERS)
  api.chromium_tests.configure_build(bot_config_object)


def GenTests(api):
  yield (
      api.test('set_component_rev') +
      api.properties.generic(
          mastername='fake.master',
          buildername='Component Rev Builder') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('android_apply_config') +
      api.properties.generic(
          mastername='fake.master',
          buildername='Android Apply Config Builder') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('chromium_tests_apply_config') +
      api.properties.generic(
          mastername='fake.master',
          buildername='Chromium Tests Apply Config Builder') +
      api.post_process(post_process.DropExpectation)
  )

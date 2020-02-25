# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/properties',
]

from recipe_engine import post_process


DUMMY_BUILDERS = {
  'chromium.fake': {
    'builders': {
      'cross-master-trigger-builder': {
        'bot_type': 'builder',
        'chromium_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
        'gclient_config': 'chromium',
      },
    },
  },
  'chromium.fake.fyi': {
    'builders': {
      'cross-master-trigger-tester': {
        'bot_type': 'tester',
        'parent_buildername': 'cross-master-trigger-builder',
        'parent_mastername': 'chromium.fake',
      }
    },
  },
}


def RunSteps(api):
  bot_config_object = api.chromium_tests.create_bot_config_object(
      [api.chromium.get_builder_id()], builders=api.properties.get('builders'))
  api.chromium_tests.configure_build(bot_config_object)
  api.chromium_tests.prepare_checkout(bot_config_object)


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          mastername='chromium.linux', builder='Linux Builder'),
  )

  yield api.test(
      'disable_tests',
      api.chromium.ci_build(
          mastername='chromium.lkgr', builder='Win ASan Release'),
  )

  yield api.test(
      'cross_master_trigger',
      api.chromium.ci_build(
          mastername='chromium.fake', builder='cross-master-trigger-builder'),
      api.properties(builders=DUMMY_BUILDERS),
      api.post_process(post_process.MustRun,
                       'read test spec (chromium.fake.fyi.json)'),
      api.post_process(post_process.DropExpectation),
  )

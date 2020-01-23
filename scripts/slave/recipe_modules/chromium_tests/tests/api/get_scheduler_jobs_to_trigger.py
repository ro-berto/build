# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]


def RunSteps(api):
  mastername = api.properties['mastername']
  buildername = api.buildbucket.builder_name
  bot_config = api.chromium_tests.create_bot_config_object(
      [api.chromium_tests.create_bot_id(mastername, buildername)])
  api.chromium_tests.configure_build(bot_config)
  _, build_config = api.chromium_tests.prepare_checkout(bot_config)
  actual = api.chromium_tests._get_scheduler_jobs_to_trigger(
      mastername, buildername, build_config)

  # Convert the mappings to comparable types
  actual = {k: set(v) for k, v in actual.iteritems()}
  expected = {k: set(v) for k, v in api.properties['expected'].iteritems()}

  api.assertions.assertEqual(actual, expected)


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(
          mastername='chromium.linux',
          builder='Linux Builder',
      ),
      api.properties(expected={
          'chromium': ['Linux Tests'],
      },),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'bucketed-triggers',
      api.chromium.ci_build(
          mastername='chromium.linux',
          builder='Linux Builder',
      ),
      api.properties(
          expected={
              'chromium': ['ci-Linux Tests'],
          },
          **{
              '$build/chromium_tests': {
                  'bucketed_triggers': True,
              },
          }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

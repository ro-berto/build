# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
  'chromium_tests',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium_tests.create_generalized_bot_config_object(
      [{'mastername': api.properties['mastername'],
        'buildername': api.properties['buildername']}],
      builders={
        'chromium.foo': {
          'builders': {
            'Foo Builder': {}
          }
        }
      })


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.generic(
          mastername='chromium.foo',
          buildername='Foo Builder') +
      api.post_process(post_process.StatusCodeIn, 0) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('missing_master_config') +
      api.properties.generic(
          mastername='chromium.bar',
          buildername='Bar Builder') +
      api.post_process(post_process.StatusCodeIn, 1) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('missing_builder_config') +
      api.properties.generic(
          mastername='chromium.foo',
          buildername='Bar Builder') +
      api.post_process(post_process.StatusCodeIn, 1) +
      api.post_process(post_process.DropExpectation)
  )

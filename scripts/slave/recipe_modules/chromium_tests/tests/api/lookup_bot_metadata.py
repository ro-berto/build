# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium_tests.lookup_bot_metadata(
      builders={
          'chromium.foo': {
              'foo-rel': {}
          },
          'tryserver.chromium.foo': {
              'foo-dbg': {}
          },
      },
      mirrored_bots={
          'tryserver.chromium.foo': {
              'foo-rel': {
                  'mirrors': [{
                      'mastername': 'chromium.foo',
                      'buildername': 'foo-rel'
                  }],
              }
          }
      })


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(mastername='chromium.foo', builder='foo-rel'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'trybot',
      api.chromium.try_build(
          mastername='tryserver.chromium.foo', builder='foo-rel'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'standalone-trybot',
      api.chromium.try_build(
          mastername='tryserver.chromium.foo', builder='foo-dbg'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, try_spec

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium_tests.lookup_bot_metadata(
      builders=bot_db.BotDatabase.create({
          'chromium.foo': {
              'foo-rel': bot_spec.BotSpec.create(),
          },
          'tryserver.chromium.foo': {
              'foo-dbg': bot_spec.BotSpec.create(),
          },
      }),
      mirrored_bots=try_spec.TryDatabase.create({
          'tryserver.chromium.foo': {
              'foo-rel':
                  try_spec.TrySpec.create(mirrors=[
                      chromium.BuilderId.create_for_group(
                          'chromium.foo', 'foo-rel'),
                  ]),
          }
      }))


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(builder_group='chromium.foo', builder='foo-rel'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'trybot',
      api.chromium.try_build(
          builder_group='tryserver.chromium.foo', builder='foo-rel'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'standalone-trybot',
      api.chromium.try_build(
          builder_group='tryserver.chromium.foo', builder='foo-dbg'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

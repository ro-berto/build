# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium.types import BuilderId
from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec

DEPS = [
    'recipe_engine/assertions',
]

EMPTY_SPEC = bot_spec.BotSpec.create()


def RunSteps(api):
  api.assertions.maxDiff = None

  db = bot_db.BotDatabase.create({
      'master-1': {
          'builder-1-a': {},
          'builder-1-b': {
              'parent_buildername': 'builder-1-a',
              'bot_type': bot_spec.TESTER,
          },
      },
      'master-2': {
          'builder-2': {
              'parent_mastername': 'master-1',
              'parent_buildername': 'builder-1-a',
              'bot_type': bot_spec.TESTER,
          },
      },
      'master-3': {
          'builder-3-a':
              bot_spec.BotSpec.create(
                  parent_buildername='builder-3-c', bot_type=bot_spec.TESTER),
          'builder-3-b': {},
          'builder-3-c': {},
      },
  })

  key_1a = BuilderId.create_for_master('master-1', 'builder-1-a')
  key_1b = BuilderId.create_for_master('master-1', 'builder-1-b')
  key_2 = BuilderId.create_for_master('master-2', 'builder-2')
  key_3a = BuilderId.create_for_master('master-3', 'builder-3-a')
  key_3b = BuilderId.create_for_master('master-3', 'builder-3-b')
  key_3c = BuilderId.create_for_master('master-3', 'builder-3-c')

  api.assertions.assertEqual(
      set(db.keys()), {key_1a, key_1b, key_2, key_3a, key_3b, key_3c})
  api.assertions.assertEqual(db[key_1a], EMPTY_SPEC)
  api.assertions.assertEqual(
      db[key_1b],
      bot_spec.BotSpec.create(
          parent_buildername='builder-1-a', bot_type=bot_spec.TESTER))
  api.assertions.assertEqual(
      db[key_2],
      bot_spec.BotSpec.create(
          parent_mastername='master-1',
          parent_buildername='builder-1-a',
          bot_type=bot_spec.TESTER,
      ))
  api.assertions.assertEqual(
      db[key_3a],
      bot_spec.BotSpec.create(
          parent_buildername='builder-3-c', bot_type=bot_spec.TESTER))
  api.assertions.assertEqual(db[key_3b], EMPTY_SPEC)
  api.assertions.assertEqual(db[key_3c], EMPTY_SPEC)

  graph = bot_db.BotGraph.create(db)
  api.assertions.assertEqual(
      dict(graph), {
          key_1a: frozenset([key_1b, key_2]),
          key_1b: frozenset([]),
          key_2: frozenset([]),
          key_3a: frozenset([]),
          key_3b: frozenset([]),
          key_3c: frozenset([key_3a]),
      })


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

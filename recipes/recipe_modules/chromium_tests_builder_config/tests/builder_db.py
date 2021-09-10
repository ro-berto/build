# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium import BuilderId
from RECIPE_MODULES.build.chromium_tests_builder_config import (builder_db,
                                                                builder_spec)

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'recipe_engine/assertions',
]

EMPTY_SPEC = builder_spec.BuilderSpec.create()


def RunSteps(api):
  api.assertions.maxDiff = None

  db = builder_db.BuilderDatabase.create({
      'group-1': {
          'builder-1-a':
              builder_spec.BuilderSpec.create(),
          'builder-1-b':
              builder_spec.BuilderSpec.create(
                  parent_buildername='builder-1-a',
                  execution_mode=builder_spec.TEST,
              ),
      },
      'group-2': {
          'builder-2':
              builder_spec.BuilderSpec.create(
                  parent_builder_group='group-1',
                  parent_buildername='builder-1-a',
                  execution_mode=builder_spec.TEST,
              ),
      },
      'group-3': {
          'builder-3-a':
              builder_spec.BuilderSpec.create(
                  parent_buildername='builder-3-c',
                  execution_mode=builder_spec.TEST),
          'builder-3-b':
              builder_spec.BuilderSpec.create(),
          'builder-3-c':
              builder_spec.BuilderSpec.create(),
      },
  })

  key_1a = BuilderId.create_for_group('group-1', 'builder-1-a')
  key_1b = BuilderId.create_for_group('group-1', 'builder-1-b')
  key_2 = BuilderId.create_for_group('group-2', 'builder-2')
  key_3a = BuilderId.create_for_group('group-3', 'builder-3-a')
  key_3b = BuilderId.create_for_group('group-3', 'builder-3-b')
  key_3c = BuilderId.create_for_group('group-3', 'builder-3-c')

  api.assertions.assertEqual(
      set(db.keys()), {key_1a, key_1b, key_2, key_3a, key_3b, key_3c})
  api.assertions.assertEqual(db[key_1a], EMPTY_SPEC)
  api.assertions.assertEqual(
      db[key_1b],
      builder_spec.BuilderSpec.create(
          parent_buildername='builder-1-a', execution_mode=builder_spec.TEST))
  api.assertions.assertEqual(
      db[key_2],
      builder_spec.BuilderSpec.create(
          parent_builder_group='group-1',
          parent_buildername='builder-1-a',
          execution_mode=builder_spec.TEST,
      ))
  api.assertions.assertEqual(
      db[key_3a],
      builder_spec.BuilderSpec.create(
          parent_buildername='builder-3-c', execution_mode=builder_spec.TEST))
  api.assertions.assertEqual(db[key_3b], EMPTY_SPEC)
  api.assertions.assertEqual(db[key_3c], EMPTY_SPEC)

  graph = db.builder_graph
  api.assertions.assertEqual(
      dict(graph), {
          key_1a: frozenset([key_1b, key_2]),
          key_1b: frozenset([]),
          key_2: frozenset([]),
          key_3a: frozenset([]),
          key_3b: frozenset([]),
          key_3c: frozenset([key_3a]),
      })

  api.assertions.assertEqual(
      graph.get_transitive_closure([key_1a, key_1b]),
      {key_1a, key_1b, key_2},
  )


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'chromium',
    'chromium_tests_builder_config',
]

BUILDER_DB = ctbc.BuilderDatabase.create({
    'fake-group': {
        'fake-builder': ctbc.BuilderSpec.create(),
    },
})

TRY_DB = ctbc.TryDatabase.create({
    'fake-try-group': {
        'fake-try-builder':
            ctbc.TrySpec.create_for_single_mirror('fake-group', 'fake-builder'),
    },
})


def RunSteps(api):
  api.chromium_tests_builder_config.lookup_builder(
      builder_db=BUILDER_DB, try_db=TRY_DB)


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(builder_group='fake-group', builder='fake-builder'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_group_config',
      api.chromium.ci_build(
          builder_group='fake-group2', builder='fake-builder2'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_builder_config',
      api.chromium.ci_build(
          builder_group='fake-group', builder='fake-builder2'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'try-builder',
      api.chromium.try_build(
          builder_group='fake-try-group', builder='fake-try-builder'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

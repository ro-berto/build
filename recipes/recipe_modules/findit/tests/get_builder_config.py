# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import six

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium_tests_builder_config',
    'findit',
    'recipe_engine/assertions',
    'recipe_engine/properties',
]


def RunSteps(api):
  target_builder_id = api.properties['target_builder_id']

  builder_config = api.findit.get_builder_config(target_builder_id)

  api.assertions.assertCountEqual(builder_config.builder_ids,
                                  api.properties['builder_ids'])
  api.assertions.assertCountEqual(
      builder_config.builder_ids_in_scope_for_testing,
      api.properties['builder_ids_in_scope_for_testing'])


def GenTests(api):
  builder_id = chromium.BuilderId.create_for_group(
      six.u('fake-group'), six.u('fake-builder'))
  tester_id = chromium.BuilderId.create_for_group(
      six.u('fake-group'), six.u('fake-tester'))

  yield api.test(
      'src-side-builder',
      api.properties(
          target_builder_id=builder_id,
          builder_ids=[builder_id],
          builder_ids_in_scope_for_testing=[builder_id],
      ),
      api.chromium_tests_builder_config \
          .properties_builder_for_ci_builder(
              builder_group=builder_id.group, builder=builder_id.builder) \
          .build(),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'src-side-tester',
      api.properties(
          target_builder_id=tester_id,
          builder_ids=[builder_id],
          builder_ids_in_scope_for_testing=[builder_id, tester_id],
      ),
      api.chromium_tests_builder_config \
          .properties_builder_for_ci_tester(
              builder_group=tester_id.group, builder=tester_id.builder) \
          .with_parent(
              builder_group=builder_id.group, builder=builder_id.builder) \
          .build(),
      api.post_process(post_process.DropExpectation),
  )

  # Target builder refers to builder other than what the src-side config has
  yield api.test(
      'bad-src-side-builder',
      api.properties(
          target_builder_id=chromium.BuilderId.create_for_group(
              'fake-group', 'other-fake-builder')),
      api.chromium_tests_builder_config \
          .properties_builder_for_ci_builder(
              builder_group=builder_id.group, builder=builder_id.builder) \
          .build(),
      api.post_check(post_process.StepException, 'invalid target builder'),
      api.post_check(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non-src-side-builder',
      api.properties(
          target_builder_id=builder_id,
          builder_ids=[builder_id],
          builder_ids_in_scope_for_testing=[builder_id],
      ),
      api.chromium_tests_builder_config.builder_db(
          ctbc.BuilderDatabase.create({
              builder_id.group: {
                  builder_id.builder:
                      ctbc.BuilderSpec.create(
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
              },
          })),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non-src-side-tester',
      api.properties(
          target_builder_id=tester_id,
          builder_ids=[builder_id],
          builder_ids_in_scope_for_testing=[builder_id, tester_id],
      ),
      api.chromium_tests_builder_config.builder_db(
          ctbc.BuilderDatabase.create({
              builder_id.group: {
                  builder_id.builder:
                      ctbc.BuilderSpec.create(
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
                  tester_id.builder:
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername=builder_id.builder,
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
                  'other-fake-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername=builder_id.builder,
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
              },
          })),
      api.post_process(post_process.DropExpectation),
  )

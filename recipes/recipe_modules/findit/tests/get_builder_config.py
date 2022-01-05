# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import six

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb
from PB.recipe_modules.build.chromium_tests_builder_config import (properties as
                                                                   properties_pb
                                                                  )

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
      api.chromium_tests_builder_config.properties(
          properties_pb.InputProperties(
              builder_config=properties_pb.BuilderConfig(
                  builder_db=properties_pb.BuilderDatabase(entries=[
                      properties_pb.BuilderDatabase.Entry(
                          builder_id=builder_pb.BuilderID(
                              project='fake-project',
                              bucket='ci',
                              builder='fake-builder',
                          ),
                          builder_spec=properties_pb.BuilderSpec(
                              builder_group='fake-group',
                              execution_mode='COMPILE_AND_TEST',
                              legacy_gclient_config=properties_pb.BuilderSpec
                              .LegacyGclientRecipeModuleConfig(
                                  config='chromium'),
                              legacy_chromium_config=properties_pb.BuilderSpec
                              .LegacyChromiumRecipeModuleConfig(
                                  config='chromium'),
                          ),
                      ),
                  ]),
                  builder_ids=[
                      builder_pb.BuilderID(
                          project='fake-project',
                          bucket='ci',
                          builder='fake-builder',
                      ),
                  ],
              ))),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'src-side-tester',
      api.properties(
          target_builder_id=tester_id,
          builder_ids=[builder_id],
          builder_ids_in_scope_for_testing=[builder_id, tester_id],
      ),
      api.chromium_tests_builder_config.properties(
          properties_pb.InputProperties(
              builder_config=properties_pb.BuilderConfig(
                  builder_db=properties_pb.BuilderDatabase(entries=[
                      properties_pb.BuilderDatabase.Entry(
                          builder_id=builder_pb.BuilderID(
                              project='fake-project',
                              bucket='ci',
                              builder='fake-builder',
                          ),
                          builder_spec=properties_pb.BuilderSpec(
                              builder_group='fake-group',
                              execution_mode='COMPILE_AND_TEST',
                              legacy_gclient_config=properties_pb.BuilderSpec
                              .LegacyGclientRecipeModuleConfig(
                                  config='chromium'),
                              legacy_chromium_config=properties_pb.BuilderSpec
                              .LegacyChromiumRecipeModuleConfig(
                                  config='chromium'),
                          ),
                      ),
                      properties_pb.BuilderDatabase.Entry(
                          builder_id=builder_pb.BuilderID(
                              project='fake-project',
                              bucket='ci',
                              builder='fake-tester',
                          ),
                          builder_spec=properties_pb.BuilderSpec(
                              builder_group='fake-group',
                              execution_mode='TEST',
                              parent=builder_pb.BuilderID(
                                  project='fake-project',
                                  bucket='ci',
                                  builder='fake-builder',
                              ),
                              legacy_gclient_config=properties_pb.BuilderSpec
                              .LegacyGclientRecipeModuleConfig(
                                  config='chromium'),
                              legacy_chromium_config=properties_pb.BuilderSpec
                              .LegacyChromiumRecipeModuleConfig(
                                  config='chromium'),
                          ),
                      ),
                  ]),
                  builder_ids=[
                      builder_pb.BuilderID(
                          project='fake-project',
                          bucket='ci',
                          builder='fake-tester',
                      ),
                  ],
              ))),
      api.post_process(post_process.DropExpectation),
  )

  # Target builder refers to builder other than what the src-side config has
  yield api.test(
      'bad-src-side-builder',
      api.properties(
          target_builder_id=chromium.BuilderId.create_for_group(
              'fake-group', 'other-fake-builder')),
      api.chromium_tests_builder_config.properties(
          properties_pb.InputProperties(
              builder_config=properties_pb.BuilderConfig(
                  builder_db=properties_pb.BuilderDatabase(entries=[
                      properties_pb.BuilderDatabase.Entry(
                          builder_id=builder_pb.BuilderID(
                              project='fake-project',
                              bucket='ci',
                              builder='fake-builder',
                          ),
                          builder_spec=properties_pb.BuilderSpec(
                              builder_group='fake-group',
                              execution_mode='COMPILE_AND_TEST',
                              legacy_gclient_config=properties_pb.BuilderSpec
                              .LegacyGclientRecipeModuleConfig(
                                  config='chromium'),
                              legacy_chromium_config=properties_pb.BuilderSpec
                              .LegacyChromiumRecipeModuleConfig(
                                  config='chromium'),
                          ),
                      ),
                  ]),
                  builder_ids=[
                      builder_pb.BuilderID(
                          project='fake-project',
                          bucket='ci',
                          builder='fake-builder',
                      ),
                  ],
              ))),
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
              'fake-group': {
                  'fake-builder':
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
              'fake-group': {
                  'fake-builder':
                      ctbc.BuilderSpec.create(
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
                  'fake-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='fake-builder',
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
                  'other-fake-tester':
                      ctbc.BuilderSpec.create(
                          execution_mode=ctbc.TEST,
                          parent_buildername='fake-builder',
                          gclient_config='chromium',
                          chromium_config='chromium',
                      ),
              },
          })),
      api.post_process(post_process.DropExpectation),
  )

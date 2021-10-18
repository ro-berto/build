# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import six

from recipe_engine import post_process, recipe_api
from recipe_engine.config import Dict

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build.chromium import BuilderId

from PB.recipe_modules.build.chromium_tests_builder_config import (properties as
                                                                   properties_pb
                                                                  )
from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'chromium_tests_builder_config',
    'recipe_engine/assertions',
    'recipe_engine/properties',
]

PROPERTIES = {
    'expected_attrs': recipe_api.Property(kind=Dict(), default={}),
    'use_static_dbs': recipe_api.Property(kind=bool, default=False),
}

BUILDER_DB = ctbc.BuilderDatabase.create({
    'fake-group': {
        'fake-builder': ctbc.BuilderSpec.create(),
    },
})

TRY_DB = ctbc.TryDatabase.create({
    'fake-try-group': {
        'fake-try-builder':
            ctbc.TrySpec.create_for_single_mirror(
                'fake-group',
                'fake-builder',
                is_compile_only=True,
                analyze_names=('foo', 'bar'),
                retry_failed_shards=False,
                retry_without_patch=False,
                regression_test_selection=ctbc.QUICK_RUN_ONLY,
                regression_test_selection_recall=0.5,
            ),
    },
})


def RunSteps(api, expected_attrs, use_static_dbs):
  lookup_kwargs = {}
  if not use_static_dbs:
    lookup_kwargs = {'builder_db': BUILDER_DB, 'try_db': TRY_DB}
  _, builder_config = api.chromium_tests_builder_config.lookup_builder(
      **lookup_kwargs)
  for k, v in six.iteritems(expected_attrs):
    value = getattr(builder_config, k)
    api.assertions.assertEqual(
        value, v,
        'Expected value of {} to be {{second}}, got {{first}}'.format(k))


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.ci_build(builder_group='fake-group', builder='fake-builder'),
      api.properties(
          expected_attrs=dict(
              mirroring_try_builders=(BuilderId.create_for_group(
                  'fake-try-group', 'fake-try-builder'),),
              builder_ids=(
                  BuilderId.create_for_group('fake-group', 'fake-builder'),),
              builder_ids_in_scope_for_testing=set(
                  [BuilderId.create_for_group('fake-group', 'fake-builder')]),
              include_all_triggered_testers=True,
              is_compile_only=False,
              analyze_names=(),
              retry_failed_shards=True,
              retry_without_patch=True,
              regression_test_selection=ctbc.NEVER,
              regression_test_selection_recall=0.95,
          )),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_group_config',
      api.chromium.ci_build(
          builder_group='fake-group2', builder='fake-builder2'),
      api.post_process(post_process.MustRun,
                       "No configuration present for group 'fake-group2'"),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing_builder_config',
      api.chromium.ci_build(
          builder_group='fake-group', builder='fake-builder2'),
      api.post_process(post_process.MustRun,
                       ('No configuration present for builder '
                        "'fake-builder2' in group 'fake-group'")),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'try-builder',
      api.chromium.try_build(
          builder_group='fake-try-group', builder='fake-try-builder'),
      api.properties(
          expected_attrs=dict(
              mirroring_try_builders=(),
              builder_ids=(
                  BuilderId.create_for_group('fake-group', 'fake-builder'),),
              builder_ids_in_scope_for_testing=set(
                  [BuilderId.create_for_group('fake-group', 'fake-builder')]),
              include_all_triggered_testers=False,
              is_compile_only=True,
              analyze_names=('foo', 'bar'),
              retry_failed_shards=False,
              retry_without_patch=False,
              regression_test_selection=ctbc.QUICK_RUN_ONLY,
              regression_test_selection_recall=0.5,
          )),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'static-dbs',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(use_static_dbs=True),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'builder-config-from-properties',
      api.chromium.ci_build(builder_group='fake-group', builder='fake-builder'),
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
                                  config='chromium',
                                  target_bits=64,
                                  target_cros_boards=[
                                      'fake-board1',
                                      'fake-board2',
                                  ]),
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
                                  config='chromium',
                                  target_bits=64,
                                  target_cros_boards=[
                                      'fake-board1',
                                      'fake-board2',
                                  ]),
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
                  builder_ids_in_scope_for_testing=[
                      builder_pb.BuilderID(
                          project='fake-project',
                          bucket='ci',
                          builder='fake-tester',
                      ),
                  ],
              ))),
      api.properties(
          expected_attrs=dict(
              builder_db=ctbc.BuilderDatabase.create({
                  'fake-group': {
                      'fake-builder':
                          ctbc.BuilderSpec.create(
                              luci_project='fake-project',
                              execution_mode=ctbc.COMPILE_AND_TEST,
                              gclient_config='chromium',
                              chromium_config='chromium',
                              chromium_config_kwargs={
                                  'TARGET_BITS':
                                      64,
                                  'TARGET_CROS_BOARDS':
                                      'fake-board1:fake-board2',
                              },
                          ),
                      'fake-tester':
                          ctbc.BuilderSpec.create(
                              luci_project='fake-project',
                              execution_mode=ctbc.TEST,
                              parent_builder_group='fake-group',
                              parent_buildername='fake-builder',
                              gclient_config='chromium',
                              chromium_config='chromium',
                              chromium_config_kwargs={
                                  'TARGET_BITS':
                                      64,
                                  'TARGET_CROS_BOARDS':
                                      'fake-board1:fake-board2',
                              },
                          ),
                  },
              }),
              mirroring_try_builders=(),
              builder_ids=(
                  BuilderId.create_for_group('fake-group', 'fake-builder'),),
              builder_ids_in_scope_for_testing=set([
                  BuilderId.create_for_group('fake-group', 'fake-builder'),
                  BuilderId.create_for_group('fake-group', 'fake-tester'),
              ]),
              include_all_triggered_testers=False,
              is_compile_only=False,
              analyze_names=(),
              retry_failed_shards=False,
              retry_without_patch=False,
              regression_test_selection=ctbc.NEVER,
              regression_test_selection_recall=0.95,
          )),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'invalid-properties',
      api.chromium.ci_build(builder_group='fake-group', builder='fake-builder'),
      api.chromium_tests_builder_config.properties(
          properties_pb.InputProperties(
              builder_config=properties_pb.BuilderConfig())),
      api.post_process(post_process.MustRun,
                       'invalid chromium_tests_builder_config properties'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

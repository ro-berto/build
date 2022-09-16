# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from PB.recipe_modules.build.chromium_tests_builder_config_migration import (
    properties as properties_pb)

DEPS = [
    'chromium_tests_builder_config',
    'chromium_tests_builder_config_migration',
    'recipe_engine/properties',
]

PROPERTIES = properties_pb.InputProperties


def RunSteps(api, properties):
  ctbc_api = api.chromium_tests_builder_config
  return api.chromium_tests_builder_config_migration(properties,
                                                     ctbc_api.builder_db,
                                                     ctbc_api.try_db)


def GenTests(api):

  def invalid_properties(*errors):
    test_data = api.post_check(post_process.StatusException)
    test_data += api.post_check(
        post_process.ResultReasonRE,
        '^The following errors were found with the input properties')
    for error in errors:
      test_data += api.post_check(post_process.ResultReasonRE, error)
    test_data += api.post_process(post_process.DropExpectation)
    return test_data

  yield api.test(
      'no-operation',
      invalid_properties('no operation is set'),
  )

  yield api.test(
      'bad-groupings-operation',
      api.properties(groupings_operation={}),
      invalid_properties(
          r'groupings_operation\.output_path is not set',
          r'groupings_operation\.builder_group_filters is empty'),
  )

  yield api.test(
      'bad-builder-group-filter',
      api.properties(groupings_operation={
          'builder_group_filters': [{}],
      }),
      invalid_properties((r'groupings_operation\.builder_group_filters\[0\]'
                          r'\.builder_group_regex is not set')),
  )

  yield api.test(
      'bad-migration-operation',
      api.properties(migration_operation={}),
      invalid_properties(r'migration_operation\.builders_to_migrate is empty',
                         r'migration_operation\.output_path is not set'),
  )

  yield api.test(
      'bad-builder-to-migrate',
      api.properties(migration_operation={
          'builders_to_migrate': [{}],
      }),
      invalid_properties(
          (r'migration_operation\.builders_to_migrate\[0\]'
           r'\.builder_group is not set'),
          r'migration_operation\.builders_to_migrate\[0\]\.builder is not set'),
  )

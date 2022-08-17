# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test recipe for valid use of property builders of the test API."""

import six

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

DEPS = [
    'chromium_tests_builder_config',
    'recipe_engine/assertions',
    'recipe_engine/json',
    'recipe_engine/properties',
]


def RunSteps(api):
  builder_id = chromium.BuilderId.create_for_group('unused-group',
                                                   'unused-builder')

  _, builder_config = api.chromium_tests_builder_config.lookup_builder(
      builder_id)

  api.assertions.assertCountEqual(builder_config.builder_ids,
                                  api.properties['expected_builder_ids'])
  api.assertions.assertCountEqual(
      builder_config.builder_ids_in_scope_for_testing,
      api.properties['expected_builder_ids_in_scope_for_testing'])

  builder_db = builder_config.builder_db
  expected_specs = api.properties['expected_specs']
  api.assertions.assertCountEqual(builder_db.keys(), expected_specs.keys())
  for builder_id, expected_spec in six.iteritems(expected_specs):
    api.assertions.assertEqual(
        builder_db[builder_id], expected_spec,
        'Spec for {}:\nexpected: {{second}}\nactual: {{first}}'.format(
            builder_id))

  for k, v in six.iteritems(api.properties.get('expected_attrs', {})):
    value = getattr(builder_config, k)
    api.assertions.assertEqual(
        value, v,
        'builder_config.{}:\nexpected: {{second}}\nactual: {{first}}'.format(k))


def GenTests(api):
  builder_id = chromium.BuilderId.create_for_group('fake-group', 'fake-builder')
  tester_id = chromium.BuilderId.create_for_group('fake-group', 'fake-tester')
  tester2_id = chromium.BuilderId.create_for_group('fake-group', 'fake-tester2')

  yield api.test(
      'builder',
      api.chromium_tests_builder_config.properties(
          api.chromium_tests_builder_config.properties_assembler_for_ci_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.properties(
          expected_builder_ids=[builder_id],
          expected_builder_ids_in_scope_for_testing=[builder_id],
          expected_specs={
              builder_id:
                  ctbc.BuilderSpec.create(
                      gclient_config='chromium',
                      chromium_config='chromium',
                  ),
          },
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'builder-with-testers',
      api.chromium_tests_builder_config.properties(
          api.chromium_tests_builder_config.properties_assembler_for_ci_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).with_tester(
              builder_group='fake-group',
              builder='fake-tester',
          ).with_tester(
              builder_group='fake-group',
              builder='fake-tester2',
          ).assemble()),
      api.properties(
          expected_builder_ids=[builder_id],
          expected_builder_ids_in_scope_for_testing=[
              builder_id,
              tester_id,
              tester2_id,
          ],
          expected_specs={
              builder_id:
                  ctbc.BuilderSpec.create(
                      gclient_config='chromium',
                      chromium_config='chromium',
                  ),
              tester_id:
                  ctbc.BuilderSpec.create(
                      execution_mode=ctbc.TEST,
                      parent_builder_group='fake-group',
                      parent_buildername='fake-builder',
                      gclient_config='chromium',
                      chromium_config='chromium',
                  ),
              tester2_id:
                  ctbc.BuilderSpec.create(
                      execution_mode=ctbc.TEST,
                      parent_builder_group='fake-group',
                      parent_buildername='fake-builder',
                      gclient_config='chromium',
                      chromium_config='chromium',
                  ),
          },
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non-default-builder-with-tester',
      api.chromium_tests_builder_config.properties(
          api.chromium_tests_builder_config.properties_assembler_for_ci_builder(
              builder_group='fake-group',
              builder='fake-builder',
              builder_spec=ctbc.BuilderSpec.create(
                  gclient_config='gclient-config',
                  chromium_config='chromium-config',
                  chromium_config_kwargs={
                      'TARGET_BITS': 64,
                      'TARGET_CROS_BOARDS': 'board:board2',
                  },
                  android_config='android-config',
                  android_apply_config=['android-apply-config'],
                  test_results_config='test-results-config',
                  skylab_gs_bucket='skylab-gs-bucket',
                  skylab_gs_extra='skylab-gs-extra',
                  cf_archive_build=True,
                  cf_gs_bucket='cf-gs-bucket',
                  cf_gs_acl='cf-gs-acl',
                  cf_archive_name='cf-archive-name',
                  cf_archive_subdir_suffix='cf-archive-subdir-suffix',
              ),
          ).with_tester(
              builder_group='fake-group',
              builder='fake-tester',
          ).assemble()),
      api.properties(
          expected_builder_ids=[builder_id],
          expected_builder_ids_in_scope_for_testing=[builder_id, tester_id],
          expected_specs={
              builder_id:
                  ctbc.BuilderSpec.create(
                      gclient_config='gclient-config',
                      chromium_config='chromium-config',
                      chromium_config_kwargs={
                          'TARGET_BITS': 64,
                          'TARGET_CROS_BOARDS': 'board:board2',
                      },
                      android_config='android-config',
                      android_apply_config=['android-apply-config'],
                      test_results_config='test-results-config',
                      skylab_gs_bucket='skylab-gs-bucket',
                      skylab_gs_extra='skylab-gs-extra',
                      cf_archive_build=True,
                      cf_gs_bucket='cf-gs-bucket',
                      cf_gs_acl='cf-gs-acl',
                      cf_archive_name='cf-archive-name',
                      cf_archive_subdir_suffix='cf-archive-subdir-suffix',
                  ),
              tester_id:
                  ctbc.BuilderSpec.create(
                      execution_mode=ctbc.TEST,
                      parent_builder_group='fake-group',
                      parent_buildername='fake-builder',
                      gclient_config='gclient-config',
                      chromium_config='chromium-config',
                      chromium_config_kwargs={
                          'TARGET_BITS': 64,
                          'TARGET_CROS_BOARDS': 'board:board2',
                      },
                      android_config='android-config',
                      android_apply_config=['android-apply-config'],
                      test_results_config='test-results-config',
                      skylab_gs_bucket='skylab-gs-bucket',
                      skylab_gs_extra='skylab-gs-extra',
                      cf_archive_build=True,
                      cf_gs_bucket='cf-gs-bucket',
                      cf_gs_acl='cf-gs-acl',
                      cf_archive_name='cf-archive-name',
                      cf_archive_subdir_suffix='cf-archive-subdir-suffix',
                  ),
          },
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'tester',
      api.chromium_tests_builder_config.properties(
          api.chromium_tests_builder_config.properties_assembler_for_ci_tester(
              builder_group='fake-group',
              builder='fake-tester',
          ).with_parent(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.properties(
          expected_builder_ids=[tester_id],
          expected_builder_ids_in_scope_for_testing=[tester_id],
          expected_specs={
              builder_id:
                  ctbc.BuilderSpec.create(
                      gclient_config='chromium',
                      chromium_config='chromium',
                  ),
              tester_id:
                  ctbc.BuilderSpec.create(
                      execution_mode=ctbc.TEST,
                      parent_builder_group='fake-group',
                      parent_buildername='fake-builder',
                      gclient_config='chromium',
                      chromium_config='chromium',
                  ),
          },
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non-default-tester',
      api.chromium_tests_builder_config.properties(
          api.chromium_tests_builder_config.properties_assembler_for_ci_tester(
              builder_group='fake-group',
              builder='fake-tester',
              builder_spec=ctbc.BuilderSpec.create(
                  gclient_config='gclient-config',
                  chromium_config='chromium-config',
              ),
          ).with_parent(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.properties(
          expected_builder_ids=[tester_id],
          expected_builder_ids_in_scope_for_testing=[tester_id],
          expected_specs={
              builder_id:
                  ctbc.BuilderSpec.create(
                      gclient_config='gclient-config',
                      chromium_config='chromium-config',
                  ),
              tester_id:
                  ctbc.BuilderSpec.create(
                      execution_mode=ctbc.TEST,
                      parent_builder_group='fake-group',
                      parent_buildername='fake-builder',
                      gclient_config='gclient-config',
                      chromium_config='chromium-config',
                  ),
          },
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'try-builder',
      api.chromium_tests_builder_config.properties(
          api.chromium_tests_builder_config
          .properties_assembler_for_try_builder(
              is_compile_only=True,
              analyze_names=['foo', 'bar'],
              retry_failed_shards=False,
              retry_without_patch=False,
              regression_test_selection=ctbc.ALWAYS,
              regression_test_selection_recall=0.5,
          ).with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).with_mirrored_tester(
              builder_group='fake-group',
              builder='fake-tester',
          ).with_mirrored_tester(
              builder_group='fake-group',
              builder='fake-tester2',
          ).assemble()),
      api.properties(
          expected_builder_ids=[builder_id],
          expected_builder_ids_in_scope_for_testing=[
              builder_id, tester_id, tester2_id
          ],
          expected_specs={
              builder_id:
                  ctbc.BuilderSpec.create(
                      gclient_config='chromium',
                      chromium_config='chromium',
                  ),
              tester_id:
                  ctbc.BuilderSpec.create(
                      execution_mode=ctbc.TEST,
                      parent_builder_group='fake-group',
                      parent_buildername='fake-builder',
                      gclient_config='chromium',
                      chromium_config='chromium',
                  ),
              tester2_id:
                  ctbc.BuilderSpec.create(
                      execution_mode=ctbc.TEST,
                      parent_builder_group='fake-group',
                      parent_buildername='fake-builder',
                      gclient_config='chromium',
                      chromium_config='chromium',
                  ),
          },
          expected_attrs={
              'is_compile_only': True,
              'analyze_names': ('foo', 'bar'),
              'retry_failed_shards': False,
              'retry_without_patch': False,
              'regression_test_selection': ctbc.ALWAYS,
              'regression_test_selection_recall': 0.5,
          },
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'try-builder-with-non-default-builder',
      api.chromium_tests_builder_config.properties(
          api.chromium_tests_builder_config
          .properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
              builder_spec=ctbc.BuilderSpec.create(
                  gclient_config='gclient-config',
                  chromium_config='chromium-config',
              ),
          ).with_mirrored_tester(
              builder_group='fake-group',
              builder='fake-tester',
          ).with_mirrored_tester(
              builder_group='fake-group',
              builder='fake-tester2',
          ).assemble()),
      api.properties(
          expected_builder_ids=[builder_id],
          expected_builder_ids_in_scope_for_testing=[
              builder_id, tester_id, tester2_id
          ],
          expected_specs={
              builder_id:
                  ctbc.BuilderSpec.create(
                      gclient_config='gclient-config',
                      chromium_config='chromium-config',
                  ),
              tester_id:
                  ctbc.BuilderSpec.create(
                      execution_mode=ctbc.TEST,
                      parent_builder_group='fake-group',
                      parent_buildername='fake-builder',
                      gclient_config='gclient-config',
                      chromium_config='chromium-config',
                  ),
              tester2_id:
                  ctbc.BuilderSpec.create(
                      execution_mode=ctbc.TEST,
                      parent_builder_group='fake-group',
                      parent_buildername='fake-builder',
                      gclient_config='gclient-config',
                      chromium_config='chromium-config',
                  ),
          },
      ),
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

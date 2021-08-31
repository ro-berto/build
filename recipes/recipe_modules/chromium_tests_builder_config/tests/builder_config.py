# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium import BuilderId
from RECIPE_MODULES.build.chromium_tests_builder_config import (
    builder_config as builder_config_module, builder_db, builder_spec, try_spec)

DEPS = [
    'recipe_engine/assertions',
    'recipe_engine/python',
    'recipe_engine/step',
]


def RunSteps(api):
  # Set up data for testing builder_config methods
  builders = builder_db.BuilderDatabase.create({
      'fake-group': {
          'fake-builder':
              builder_spec.BuilderSpec.create(),
          'fake-tester':
              builder_spec.BuilderSpec.create(
                  execution_mode=builder_spec.TEST,
                  parent_buildername='fake-builder',
              ),
      },
      'fake-group2': {
          'fake-builder2': builder_spec.BuilderSpec.create(),
      },
      'fake-group3': {
          'fake-tester2':
              builder_spec.BuilderSpec.create(
                  execution_mode=builder_spec.TEST,
                  parent_builder_group='fake-group',
                  parent_buildername='fake-builder',
              ),
      },
  })

  # Test create failures
  with api.assertions.assertRaises(
      builder_config_module.BuilderConfigException) as caught:
    builder_config_module.BuilderConfig.create(
        builders,
        try_spec.TrySpec.create_for_single_mirror(
            builder_group='non-existent-group', buildername='fake-builder'))
  message = "No configuration present for group 'non-existent-group'"
  api.assertions.assertEqual(str(caught.exception), message)

  with api.assertions.assertRaises(
      builder_config_module.BuilderConfigException) as caught:
    builder_config_module.BuilderConfig.create(
        builders,
        try_spec.TrySpec.create_for_single_mirror(
            builder_group='fake-group', buildername='non-existent-builder'))
  message = ("No configuration present for builder 'non-existent-builder'"
             " in group 'fake-group'")
  api.assertions.assertEqual(str(caught.exception), message)

  # Test create failure when using python API
  with api.assertions.assertRaises(api.step.InfraFailure) as caught:
    builder_config_module.BuilderConfig.create(
        builders,
        try_spec.TrySpec.create_for_single_mirror(
            builder_group='non-existent-group', buildername='fake-builder'),
        python_api=api.python)
  name = "No configuration present for group 'non-existent-group'"
  api.assertions.assertEqual(caught.exception.result.name, name)

  # Test builder config
  mirrors = [
      try_spec.TryMirror.create(
          builder_group='fake-group',
          buildername='fake-builder',
          tester='fake-tester'),
      try_spec.TryMirror.create(
          builder_group='fake-group2',
          buildername='fake-builder2',
          tester_group='fake-group3',
          tester='fake-tester2'),
  ]
  builder_config = builder_config_module.BuilderConfig.create(
      builders, try_spec.TrySpec.create(mirrors))
  builder_config_with_try_overrides = (
      builder_config_module.BuilderConfig.create(
          builders,
          try_spec.TrySpec.create(
              mirrors,
              execution_mode=try_spec.COMPILE,
              analyze_names=['analyze-name'],
              retry_failed_shards=False,
              retry_without_patch=False,
              regression_test_selection=try_spec.ALWAYS,
              regression_test_selection_recall=0.5)))

  # Test builders_id property
  api.assertions.assertEqual(builder_config.builder_ids, (
      BuilderId.create_for_group('fake-group', 'fake-builder'),
      BuilderId.create_for_group('fake-group2', 'fake-builder2'),
  ))

  # Test mirrors property
  api.assertions.assertEqual(builder_config.mirrors, tuple(mirrors))

  # Test analyze_names property
  api.assertions.assertEqual(builder_config.analyze_names, ())
  api.assertions.assertEqual(builder_config_with_try_overrides.analyze_names,
                             ('analyze-name',))

  # Test retry_failed_shards property
  api.assertions.assertTrue(builder_config.retry_failed_shards)
  api.assertions.assertFalse(
      builder_config_with_try_overrides.retry_failed_shards)

  # Test retry_without_patch property
  api.assertions.assertTrue(builder_config.retry_without_patch)
  api.assertions.assertFalse(
      builder_config_with_try_overrides.retry_without_patch)

  # Test is_compile_only property
  api.assertions.assertFalse(builder_config.is_compile_only)
  api.assertions.assertTrue(builder_config_with_try_overrides.is_compile_only)

  # Test regression_test_selection property
  api.assertions.assertEqual(try_spec.NEVER,
                             builder_config.regression_test_selection)
  api.assertions.assertEqual(
      try_spec.ALWAYS,
      builder_config_with_try_overrides.regression_test_selection)

  # Test regression_test_selection_recall property
  api.assertions.assertEqual(
      builder_config_with_try_overrides.regression_test_selection_recall, 0.5)

  # Test source_side_spec_files property
  api.assertions.assertEqual(
      builder_config.source_side_spec_files, {
          'fake-group': 'fake-group.json',
          'fake-group2': 'fake-group2.json',
          'fake-group3': 'fake-group3.json'
      })


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

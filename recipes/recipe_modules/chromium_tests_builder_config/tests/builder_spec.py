# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests_builder_config import builder_spec

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'recipe_engine/assertions',
]


def RunSteps(api):
  api.assertions.maxDiff = None

  # Test evolve method
  empty_spec = builder_spec.BuilderSpec.create()
  api.assertions.assertIsNone(empty_spec.chromium_config)

  spec = empty_spec.evolve(chromium_config='foo')
  api.assertions.assertEqual(spec.chromium_config, 'foo')
  api.assertions.assertIsNone(empty_spec.chromium_config)

  spec2 = spec.evolve(chromium_config='bar')
  api.assertions.assertEqual(spec2.chromium_config, 'bar')
  api.assertions.assertEqual(spec.chromium_config, 'foo')
  api.assertions.assertIsNone(empty_spec.chromium_config)

  # Test extend method
  api.assertions.assertEqual(empty_spec.chromium_apply_config, ())

  spec = empty_spec.extend(chromium_apply_config=['foo', 'bar'])
  api.assertions.assertEqual(spec.chromium_apply_config, ('foo', 'bar'))
  api.assertions.assertEqual(empty_spec.chromium_apply_config, ())

  spec2 = spec.extend(chromium_apply_config=['baz', 'shaz'])
  api.assertions.assertEqual(spec2.chromium_apply_config,
                             ('foo', 'bar', 'baz', 'shaz'))
  api.assertions.assertEqual(spec.chromium_apply_config, ('foo', 'bar'))
  api.assertions.assertEqual(empty_spec.chromium_apply_config, ())

  # Test validation ************************************************************

  # execution_mode validations *************************************************
  tester_spec = builder_spec.BuilderSpec.create(
      execution_mode=builder_spec.TEST,
      parent_buildername='fake-parent',
  )

  # Testers must specify parent
  message = 'Test-only builder must specify a parent builder'
  with api.assertions.assertRaises(AssertionError) as caught:
    builder_spec.BuilderSpec.create(execution_mode=builder_spec.TEST)
  api.assertions.assertEqual(str(caught.exception), message)

  with api.assertions.assertRaises(AssertionError) as caught:
    tester_spec.evolve(parent_buildername=None)
  api.assertions.assertEqual(str(caught.exception), message)

  # Invalid fields for TEST execution_mode
  message = (
      "The following fields are ignored unless 'execution_mode' is {!r}: {}"
      .format(builder_spec.COMPILE_AND_TEST, ['compile_targets']))
  with api.assertions.assertRaises(AssertionError) as caught:
    builder_spec.BuilderSpec.create(
        execution_mode=builder_spec.TEST,
        parent_buildername='fake-builder',
        compile_targets=['foo', 'bar'],
    )
  api.assertions.assertEqual(str(caught.exception), message)

  # cf_archive_build validations ***********************************************
  cf_archive_build_spec = builder_spec.BuilderSpec.create(
      cf_archive_build=True,
      cf_gs_bucket='bucket',
      cf_gs_acl='acl',
      cf_archive_name='archive-name',
      cf_archive_subdir_suffix='archive-subdir-suffix',
  )

  # Required field when cf_archive_build is True
  message = "'cf_gs_bucket' must be provided when 'cf_archive_build' is True"
  with api.assertions.assertRaises(AssertionError) as caught:
    builder_spec.BuilderSpec.create(cf_archive_build=True)
  api.assertions.assertEqual(str(caught.exception), message)

  with api.assertions.assertRaises(AssertionError) as caught:
    cf_archive_build_spec.evolve(cf_gs_bucket=None)
  api.assertions.assertEqual(str(caught.exception), message)

  # Invalid fields when cf_archive_build is falsey
  message = ('The following fields are ignored unless '
             "'cf_archive_build' is set to True: {}".format([
                 'cf_gs_bucket', 'cf_archive_name', 'cf_gs_acl',
                 'cf_archive_subdir_suffix'
             ]))
  with api.assertions.assertRaises(AssertionError) as caught:
    builder_spec.BuilderSpec.create(
        cf_gs_bucket='bucket',
        cf_gs_acl='acl',
        cf_archive_name='archive-name',
        cf_archive_subdir_suffix='archive-subdir-suffix',
    )
  api.assertions.assertEqual(str(caught.exception), message)

  # bisect_archive_build validations *******************************************
  bisect_archive_build_spec = builder_spec.BuilderSpec.create(
      bisect_archive_build=True,
      bisect_gs_bucket='bucket',
      bisect_gs_extra='extra',
  )

  # Required field when bisect_archive_build is True
  message = (
      "'bisect_gs_bucket' must be provided when 'bisect_archive_build' is True")
  with api.assertions.assertRaises(AssertionError) as caught:
    builder_spec.BuilderSpec.create(bisect_archive_build=True)
  api.assertions.assertEqual(str(caught.exception), message)

  with api.assertions.assertRaises(AssertionError) as caught:
    bisect_archive_build_spec.evolve(bisect_gs_bucket=None)
  api.assertions.assertEqual(str(caught.exception), message)

  # Invalid fields when bisect_archive_build is falsey
  message = ('The following fields are ignored unless '
             "'bisect_archive_build' is set to True: {}".format(
                 ['bisect_gs_bucket', 'bisect_gs_extra']))
  with api.assertions.assertRaises(AssertionError) as caught:
    builder_spec.BuilderSpec.create(
        bisect_gs_bucket='bucket',
        bisect_gs_extra='extra',
    )
  api.assertions.assertEqual(str(caught.exception), message)


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

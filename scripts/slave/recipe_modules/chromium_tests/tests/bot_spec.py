# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr

from recipe_engine import post_process
from recipe_engine.types import freeze

from RECIPE_MODULES.build.chromium_tests import bot_spec

DEPS = [
    'recipe_engine/assertions',
]


def RunSteps(api):
  api.assertions.maxDiff = None

  # Test evolve method
  empty_spec = bot_spec.BotSpec.create()
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

  # bot_type validations *******************************************************
  tester_spec = bot_spec.BotSpec.create(
      bot_type=bot_spec.TESTER,
      parent_buildername='fake-parent',
  )

  # Testers must specify parent
  message = 'Tester-only bot must specify a parent builder'
  with api.assertions.assertRaises(AssertionError) as caught:
    bot_spec.BotSpec.create(bot_type=bot_spec.TESTER)
  api.assertions.assertEqual(caught.exception.message, message)

  with api.assertions.assertRaises(AssertionError) as caught:
    tester_spec.evolve(parent_buildername=None)
  api.assertions.assertEqual(caught.exception.message, message)

  # Invalid fields for non-builder bot_type
  message = (
      "The following fields are ignored unless 'bot_type' is one of {}: {}"
      .format(bot_spec.BUILDER_TYPES, ['compile_targets']))
  with api.assertions.assertRaises(AssertionError) as caught:
    bot_spec.BotSpec.create(
        bot_type=bot_spec.TESTER,
        parent_buildername='fake-builder',
        compile_targets=['foo', 'bar'],
    )
  api.assertions.assertEqual(caught.exception.message, message)

  # archive_build validations **************************************************
  archive_build_spec = bot_spec.BotSpec.create(
      archive_build=True,
      gs_bucket='bucket',
      gs_acl='acl',
      gs_build_name='build-name',
  )

  # Required field when archive_build is True
  message = "'gs_bucket' must be provided when 'archive_build' is True"
  with api.assertions.assertRaises(AssertionError) as caught:
    bot_spec.BotSpec.create(archive_build=True)
  api.assertions.assertEqual(caught.exception.message, message)

  with api.assertions.assertRaises(AssertionError) as caught:
    archive_build_spec.evolve(gs_bucket=None)
  api.assertions.assertEqual(caught.exception.message, message)

  # Invalid fields when archive_build is falsey
  message = ('The following fields are ignored unless '
             "'archive_build' is set to True: {}".format(
                 ['gs_bucket', 'gs_acl', 'gs_build_name']))
  with api.assertions.assertRaises(AssertionError) as caught:
    bot_spec.BotSpec.create(
        gs_bucket='bucket',
        gs_acl='acl',
        gs_build_name='build-name',
    )
  api.assertions.assertEqual(caught.exception.message, message)

  # cf_archive_build validations ***********************************************
  cf_archive_build_spec = bot_spec.BotSpec.create(
      cf_archive_build=True,
      cf_gs_bucket='bucket',
      cf_gs_acl='acl',
      cf_archive_name='archive-name',
      cf_archive_subdir_suffix='archive-subdir-suffix',
  )

  # Required field when cf_archive_build is True
  message = "'cf_gs_bucket' must be provided when 'cf_archive_build' is True"
  with api.assertions.assertRaises(AssertionError) as caught:
    bot_spec.BotSpec.create(cf_archive_build=True)
  api.assertions.assertEqual(caught.exception.message, message)

  with api.assertions.assertRaises(AssertionError) as caught:
    cf_archive_build_spec.evolve(cf_gs_bucket=None)
  api.assertions.assertEqual(caught.exception.message, message)

  # Invalid fields when cf_archive_build is falsey
  message = ('The following fields are ignored unless '
             "'cf_archive_build' is set to True: {}".format([
                 'cf_gs_bucket', 'cf_archive_name', 'cf_gs_acl',
                 'cf_archive_subdir_suffix'
             ]))
  with api.assertions.assertRaises(AssertionError) as caught:
    bot_spec.BotSpec.create(
        cf_gs_bucket='bucket',
        cf_gs_acl='acl',
        cf_archive_name='archive-name',
        cf_archive_subdir_suffix='archive-subdir-suffix',
    )
  api.assertions.assertEqual(caught.exception.message, message)

  # bisect_archive_build validations *******************************************
  bisect_archive_build_spec = bot_spec.BotSpec.create(
      bisect_archive_build=True,
      bisect_gs_bucket='bucket',
      bisect_gs_extra='extra',
  )

  # Required field when bisect_archive_build is True
  message = (
      "'bisect_gs_bucket' must be provided when 'bisect_archive_build' is True")
  with api.assertions.assertRaises(AssertionError) as caught:
    bot_spec.BotSpec.create(bisect_archive_build=True)
  api.assertions.assertEqual(caught.exception.message, message)

  with api.assertions.assertRaises(AssertionError) as caught:
    bisect_archive_build_spec.evolve(bisect_gs_bucket=None)
  api.assertions.assertEqual(caught.exception.message, message)

  # Invalid fields when bisect_archive_build is falsey
  message = ('The following fields are ignored unless '
             "'bisect_archive_build' is set to True: {}".format(
                 ['bisect_gs_bucket', 'bisect_gs_extra']))
  with api.assertions.assertRaises(AssertionError) as caught:
    bot_spec.BotSpec.create(
        bisect_gs_bucket='bucket',
        bisect_gs_extra='extra',
    )
  api.assertions.assertEqual(caught.exception.message, message)


def GenTests(api):
  yield api.test(
      'full',
      api.post_check(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

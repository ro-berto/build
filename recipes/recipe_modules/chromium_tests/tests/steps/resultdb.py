# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import try_spec as try_spec_module
from RECIPE_MODULES.build.chromium_tests.steps import ResultDB

DEPS = [
    'chromium',
    'chromium_tests',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    "recipe_engine/resultdb",
]


def RunSteps(api):
  cmd = ["echo", "foo"]
  bvar = 'builder:Linux Tests'

  rdb = ResultDB.create(enable=False)
  api.assertions.assertEqual(
      rdb.wrap(api, cmd),
      cmd,
  )

  # test_location_base, test_id_prefix, coerce_negative_duration
  rdb = ResultDB.create(enable=True, coerce_negative_duration=False)
  api.assertions.assertEqual(
      rdb.wrap(api, cmd),
      ['rdb', 'stream', '-var', bvar, '--'] + cmd,
  )
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, test_location_base='//path'),
      ['rdb', 'stream', '-var', bvar, '-test-location-base', '//path', '--'] +
      cmd,
  )
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, test_id_prefix='blink_web_tests'),
      [
          'rdb', 'stream', '-test-id-prefix', 'blink_web_tests', '-var', bvar,
          '--'
      ] + cmd,
  )
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, coerce_negative_duration=True),
      ['rdb', 'stream', '-var', bvar, '-coerce-negative-duration', '--'] + cmd,
  )

  # step_name
  rdb = ResultDB.create(enable=True, coerce_negative_duration=False)
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, step_name='test1'),
      ['rdb', 'stream', '-var', bvar, '-tag', 'step_name:test1', '--'] + cmd,
  )

  # base_tags
  rdb = ResultDB.create(
      enable=True, coerce_negative_duration=False, base_tags=[('k1', 'v1')])
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, base_tags=[('k2', 'v2')]),
      ['rdb', 'stream', '-var', bvar, '-tag', 'k1:v1', '-tag', 'k2:v2', '--'] +
      cmd,
  )
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, base_tags=[('k1', 'v1')]),
      ['rdb', 'stream', '-var', bvar, '-tag', 'k1:v1', '-tag', 'k1:v1', '--'] +
      cmd,
  )

  # base_variant
  rdb = ResultDB.create(
      enable=True, coerce_negative_duration=False, base_variant={"k1": "v1"})
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, base_variant={"k1": "v2"}),
      ['rdb', 'stream', '-var', bvar, '-var', 'k1:v2', '--'] + cmd,
  )
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, base_variant={"k2": "v2"}),
      ['rdb', 'stream', '-var', bvar, '-var', 'k1:v1', '-var', 'k2:v2', '--'] +
      cmd,
  )

  # result_format
  rdb = ResultDB.create(enable=True, coerce_negative_duration=False)
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, result_format='gtest'),
      ['rdb', 'stream', '-var', bvar, '--'] + [
          'result_adapter', 'gtest', '-artifact-directory',
          '${ISOLATED_OUTDIR}', '-result-file',
          '${ISOLATED_OUTDIR}/output.json', '--'
      ] + cmd,
  )
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, result_format='gtest', test_id_as_test_location=True),
      ['rdb', 'stream', '-var', bvar, '--'] +
      # test_id_as_test_location should be ignore, as the format is not json.
      [
          'result_adapter', 'gtest', '-artifact-directory',
          '${ISOLATED_OUTDIR}', '-result-file',
          '${ISOLATED_OUTDIR}/output.json', '--'
      ] + cmd,
  )
  api.assertions.assertEqual(
      rdb.wrap(api, cmd, result_format='json', test_id_as_test_location=True),
      ['rdb', 'stream', '-var', bvar, '--'] + [
          'result_adapter', 'json', '-artifact-directory', '${ISOLATED_OUTDIR}',
          '-result-file', '${ISOLATED_OUTDIR}/output.json', '-test-location',
          '--'
      ] + cmd,
  )


def GenTests(api):
  yield api.test(
      'test_results',
      api.chromium.ci_build(
          builder_group='chromium.linux',
          builder='Linux Tests',
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

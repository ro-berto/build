# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'code_coverage',
    'filter',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/buildbucket',
    'recipe_engine/runtime',
    'test_utils',
]


def RunSteps(api):
  api.path.mock_add_paths(
      api.code_coverage.profdata_dir().join('merged.profdata'))
  raw_result = api.chromium_tests.trybot_steps_for_tests(
      tests=api.properties.get('tests'))
  assert api.chromium_tests.is_precommit_mode()
  return raw_result


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.try_build(
          mastername='tryserver.chromium.linux',
          builder='linux-rel',
      ),
      api.properties(tests=['base_unittests'],),
      api.runtime(is_experimental=False, is_luci=True),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.filter.suppress_analyze(),
  )

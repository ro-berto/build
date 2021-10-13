# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.build.chromium_tests.api import ALL_TEST_BINARIES_ISOLATE_NAME

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'isolate',
    'recipe_engine/path',
    'recipe_engine/properties',
]


def RunSteps(api):
  browser_test_path = api.path['checkout'].join('out/Release/browser_tests')
  api.isolate.write_isolate_files_for_binary_file_paths(
      file_paths=[browser_test_path],
      isolate_target_name=ALL_TEST_BINARIES_ISOLATE_NAME,
      build_dir=api.path['checkout'].join('out', 'Release'),
  )


def GenTests(api):
  yield api.test(
      'basic',
      api.post_process(post_process.MustRunRE,
                       r'.*{}.isolate'.format(ALL_TEST_BINARIES_ISOLATE_NAME)),
      api.post_process(
          post_process.MustRunRE,
          r'.*{}.isolated.gen.json'.format(ALL_TEST_BINARIES_ISOLATE_NAME)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.build.chromium_tests.api import ALL_TEST_BINARIES_ISOLATE_NAME

DEPS = [
    'isolate',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/properties',
]


def RunSteps(api):
  isolated_input = 'd3854a218981bc0b25893f6d2e791cc44f198b08'
  out_dir = api.path['checkout'].join('out/Release')
  api.file.ensure_directory('ensure output directory', out_dir)
  api.isolate.download_isolate(
      'downloading {}'.format(ALL_TEST_BINARIES_ISOLATE_NAME),
      isolated_input=isolated_input,
      directory=out_dir)


def GenTests(api):
  yield api.test(
      'basic_isolate',
      api.post_process(post_process.MustRun,
                       'downloading {}'.format(ALL_TEST_BINARIES_ISOLATE_NAME)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

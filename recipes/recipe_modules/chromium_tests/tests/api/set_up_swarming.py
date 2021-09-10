# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/assertions',
    'recipe_engine/platform',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium.types import BuilderId
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc


def RunSteps(api):
  _, builder_config = api.chromium_tests_builder_config.lookup_builder(
      BuilderId.create_for_group('test_group', 'test_buildername'),
      builder_db=ctbc.BuilderDatabase.create({
          'test_group': {
              'test_buildername':
                  ctbc.BuilderSpec.create(
                      swarming_server='https://example/swarming',
                  ),
          },
      }))

  api.chromium_tests.set_up_swarming(builder_config)
  api.assertions.assertEqual(api.chromium_swarming.swarming_server,
                             'https://example/swarming')


def GenTests(api):
  yield api.test(
      'luci',
      api.platform.name('linux'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

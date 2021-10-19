# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests.steps import ResultDB

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'chromium_android',
    'recipe_engine/buildbucket',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.set_config('main_builder')
  api.chromium_android.run_test_suite('test_suite', shard_timeout=1200)
  api.chromium_android.run_test_suite(
      'test_suite-with-rdb', resultdb=ResultDB.create(enable=True))


def GenTests(api):
  yield api.test('basic', api.buildbucket.try_build())

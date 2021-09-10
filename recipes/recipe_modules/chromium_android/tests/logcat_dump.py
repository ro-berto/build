# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_android',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.set_config('try_builder')
  api.chromium_android.c.logcat_bucket = api.properties.get('logcat_bucket')
  api.chromium_android.logcat_dump()


def GenTests(api):
  yield api.test('basic', api.buildbucket.try_build(),
                 api.properties(logcat_bucket='test-bucket'),
                 api.post_process(post_process.MustRun, 'logcat_dump'),
                 api.post_process(post_process.MustRun, 'gsutil upload'),
                 api.post_process(post_process.StatusSuccess),
                 api.post_process(post_process.DropExpectation))

  yield api.test('no-bucket', api.buildbucket.try_build(),
                 api.post_process(post_process.MustRun, 'logcat_dump'),
                 api.post_process(post_process.DoesNotRun, 'gsutil upload'),
                 api.post_process(post_process.StatusSuccess),
                 api.post_process(post_process.DropExpectation))

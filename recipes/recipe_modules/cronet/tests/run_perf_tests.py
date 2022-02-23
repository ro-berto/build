# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
  'chromium',
  'chromium_android',
  'cronet',
  'recipe_engine/properties',
]


def RunSteps(api):
  return api.cronet.run_perf_tests('sample-perf-id')


def GenTests(api):
  yield api.test(
      'compile_failure',
      api.properties.generic(buildername='local_test'),
      api.step_data('compile', retcode=1),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.set_config('main_builder')
  api.chromium_android.run_instrumentation_suite(
      'test_suite',
      num_retries=5,
      tool='test_tool',
      verbose=True)


def GenTests(api):
  yield api.test('basic')

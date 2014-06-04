# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'v8',
]


def GenSteps(api):
  # Minimalistic example for running the performance tests.
  api.v8.set_config('v8')
  yield api.gclient.checkout()
  yield api.v8.runperf(['experimental'], api.v8.PERF_CONFIGS)


def GenTests(api):
  yield (
    api.test('perf_failures') +
    api.v8(perf_failures=True)
  )

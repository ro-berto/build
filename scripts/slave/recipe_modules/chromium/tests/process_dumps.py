# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium.process_dumps()


def GenTests(api):
  yield api.test('success')

  yield (
      api.test('failure') +
      api.step_data('process_dumps', retcode=1)
  )

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'isolate',
]


def RunSteps(api):
  api.chromium.set_config('chromium')

  api.isolate.remove_build_metadata()


def GenTests(api):
  yield api.test('basic')

  yield (
      api.test('failure') +
      api.step_data('remove_build_metadata', retcode=1)
  )

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'build',
  'chromium',
  'chromium_android',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium_android.upload_build('test-bucket', 'test/path')


def GenTests(api):
  yield api.test('basic')

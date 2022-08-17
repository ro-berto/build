# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium_android',
]


def RunSteps(api):
  api.chromium_android.set_config('main_builder', REPO_NAME='src')
  api.chromium_android.init_and_sync()


def GenTests(api):
  yield api.test('basic')

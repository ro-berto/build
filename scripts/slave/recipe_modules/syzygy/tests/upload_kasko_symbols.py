# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'syzygy',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.syzygy.set_config('syzygy_official')

  api.syzygy.upload_kasko_symbols()


def GenTests(api):
  yield api.test('basic')

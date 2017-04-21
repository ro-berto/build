# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'depot_tools/bot_update',
  'depot_tools/gclient',
]


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')

  update_step = api.bot_update.ensure_checkout()
  api.chromium_android.upload_apks_for_bisect(
      update_properties=update_step.json.output['properties'],
      bucket='test-bucket',
      path='test/%s/path')


def GenTests(api):
  yield api.test('basic')

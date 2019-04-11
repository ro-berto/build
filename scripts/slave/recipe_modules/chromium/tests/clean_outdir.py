# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'depot_tools/gclient',
  'depot_tools/bot_update',
]

def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')
  api.bot_update.ensure_checkout()

  api.chromium.compile()
  api.chromium.clean_outdir()


def GenTests(api):
  yield (
      api.test('basic')
  )


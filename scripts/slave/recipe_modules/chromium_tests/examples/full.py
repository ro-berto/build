# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/buildbucket',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.gclient.set_config('chromium')
  api.bot_update.ensure_checkout()

def GenTests(api):
  yield api.test('basic', api.buildbucket.try_build())

# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/buildbucket',
    'recipe_engine/step'
]

def RunSteps(api):
  api.step('Print Hello World', cmd=['echo', 'hello', 'world'])
  api.gclient.set_config('emscripten_releases')
  api.bot_update.ensure_checkout()

def GenTests(api):
  yield api.test('basic')

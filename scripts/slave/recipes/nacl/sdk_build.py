# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'depot_tools/gclient',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.chromium.apply_config('mb')
  api.gclient.set_config('chromium')
  api.bot_update.ensure_checkout()
  api.chromium.ensure_goma()
  api.chromium.runhooks()
  api.chromium.run_mb(
      api.properties.get('mastername'), api.properties.get('buildername'))

  api.python(
      'annotated_steps',
      api.path['checkout'].join(
          'native_client_sdk', 'src', 'build_tools', 'buildbot_run.py'),
      allow_subannotations=True)


def GenTests(api):
  yield (
    api.test('basic') +
    api.properties.generic() +
    api.platform('linux', 64)
  )

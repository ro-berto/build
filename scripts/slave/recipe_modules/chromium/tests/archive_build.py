# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/properties',
  'recipe_engine/runtime',
]


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')
  api.chromium.set_config('android', TARGET_PLATFORM='android')

  update_step = api.bot_update.ensure_checkout()
  api.chromium.set_build_properties(update_step.json.output['properties'])

  api.chromium.archive_build(
      'archive build',
      'sample-bucket',
      gs_acl='public',
      mode='dev')


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(buildername='test_buildername')
  )

  yield (
      api.test('experimental') +
      api.properties(buildername='test_buildername') +
      api.runtime(is_luci=True, is_experimental=True)
  )

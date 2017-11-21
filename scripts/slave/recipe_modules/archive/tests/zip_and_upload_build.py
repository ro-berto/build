# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter

DEPS = [
  'archive',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/runtime',
]


def RunSteps(api):
  api.gclient.set_config('chromium')

  bot_update_step = api.bot_update.ensure_checkout()

  api.archive.zip_and_upload_build(
      step_name='zip build',
      target=api.path['checkout'].join('Release', 'out'),
      build_url=api.archive.legacy_upload_url(
          'example_bucket', 'extra_component'),
      build_revision='example_sha',
      cros_board='daisy',
      package_dsym_files=True,
      exclude_files='example_exclude',
      exclude_perf_test_files=True,
      platform=api.properties['platform'],
      update_properties=bot_update_step.presentation.properties,
      store_by_hash=False)


def GenTests(api):
  for platform in ('linux', 'mac', 'win'):
    yield (
        api.test(platform) +
        api.runtime(is_luci=True, is_experimental=False) +
        api.properties(
            buildername='example_buildername',
            gs_acl='public',
            platform=platform)
    )
  yield (
      api.test('linux-experimental') +
      api.runtime(is_luci=False, is_experimental=True) +
      api.properties(
          buildername='example_buildername',
          gs_acl='public',
          platform='linux') +
      api.post_process(Filter('zip build'))
  )

# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'v8',
]

def RunSteps(api):
  api.gclient.set_config('chromium')
  api.gclient.apply_config('v8')

  # Chromium and V8 side-by-side makes the got_revision mapping ambiguous.
  api.gclient.c.got_revision_mapping.pop('src', None)

  api.bot_update.ensure_checkout(
      no_shallow=True, with_branch_heads=True)
  with api.context(cwd=api.path['start_dir'].join('v8')):
    safe_buildername = ''.join(
      c if c.isalnum() else '_' for c in api.properties['buildername'])
    api.step(
        'V8Releases',
        [api.path['start_dir'].join(
             'v8', 'tools', 'release', 'releases.py'),
         '-c', api.path['checkout'],
         '--json', api.path['cleanup'].join('v8-releases-update.json'),
         '--branch', 'recent',
         '--work-dir', api.path['cache'].join(safe_buildername, 'workdir')],
      )
  api.gsutil.upload(api.path['cleanup'].join('v8-releases-update.json'),
                    'chromium-v8-auto-roll',
                    api.path.join('v8rel', 'v8-releases-update.json'))


def GenTests(api):
  yield api.test('standard') + api.properties.generic(
      mastername='client.v8.fyi')


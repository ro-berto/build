# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/gsutil',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'v8',
]

def RunSteps(api):
  api.gclient.set_config('chromium')
  api.gclient.apply_config('v8')
  api.bot_update.ensure_checkout(
      no_shallow=True, with_branch_heads=True)
  with api.step.context({'cwd': api.path['start_dir'].join('v8')}):
    api.step(
        'V8Releases',
        [api.path['start_dir'].join(
             'v8', 'tools', 'release', 'releases.py'),
         '-c', api.path['checkout'],
         '--json', api.path['start_dir'].join('v8-releases-update.json'),
         '--branch', 'recent',
         '--work-dir', api.path['start_dir'].join('workdir')],
      )
  api.gsutil.upload(api.path['start_dir'].join('v8-releases-update.json'),
                    'chromium-v8-auto-roll',
                    api.path.join('v8rel', 'v8-releases-update.json'))


def GenTests(api):
  yield api.test('standard') + api.properties.generic(
      mastername='client.v8.fyi')


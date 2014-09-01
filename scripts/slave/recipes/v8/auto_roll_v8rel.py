# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'gclient',
  'gsutil',
  'json',
  'path',
  'properties',
  'step',
  'zip',
]

def GenSteps(api):
  if not api.path.exists(api.path['slave_build'].join('v8')):
    api.gsutil.download_url(
        'gs://chromium-v8-auto-roll/bootstrap/v8.zip',
        api.path['slave_build'],
        name='bootstrapping checkout')
    api.zip.unzip('unzipping',
                  api.path['slave_build'].join('v8.zip'),
                  api.path['slave_build'].join('v8'))
  api.gclient.set_config('chromium')
  # FIXME(machenbach): Branch heads are checked out for sub projects
  # not chromium.
  api.bot_update.ensure_checkout(
      force=True, no_shallow=True, with_branch_heads=True)
  api.step(
      'V8Releases',
      [api.path['slave_build'].join(
           'v8', 'tools', 'push-to-trunk', 'releases.py'),
       '-c', api.path['checkout'],
       '--branch', 'recent'],
      cwd=api.path['slave_build'].join('v8'),
    )

def GenTests(api):
  yield api.test('standard') + api.properties.generic(mastername='client.v8')

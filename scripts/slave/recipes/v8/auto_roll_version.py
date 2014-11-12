# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'path',
  'properties',
  'python',
  'step',
]

def GenSteps(api):
  api.chromium.cleanup_temp()
  api.gclient.set_config('v8')
  api.bot_update.ensure_checkout(force=True, no_shallow=True)
  api.python(
      'increment version',
      api.path['checkout'].join(
          'tools', 'push-to-trunk', 'bump_up_version.py'),
      ['--author', 'v8-autoroll@chromium.org',
       '--work-dir', api.path['slave_build'].join('workdir')],
      cwd=api.path['checkout'],
    )


def GenTests(api):
  yield api.test('standard') + api.properties.generic(mastername='client.v8')

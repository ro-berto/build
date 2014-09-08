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
]

def GenSteps(api):
  api.chromium.cleanup_temp()
  api.gclient.set_config('chromium')
  api.gclient.apply_config('v8_bleeding_edge_git')
  api.bot_update.ensure_checkout(force=True, no_shallow=True)

  api.python(
      'roll deps',
      api.path['checkout'].join(
          'v8', 'tools', 'push-to-trunk', 'auto_roll.py'),
      ['--chromium', api.path['checkout'],
       '--author', 'v8-autoroll@chromium.org',
       '--reviewer', 'machenbach@chromium.org',
       '--roll'],
      cwd=api.path['checkout'].join('v8'),
    )


def GenTests(api):
  yield api.test('standard') + api.properties.generic(mastername='client.v8')

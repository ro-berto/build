# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]


def RunSteps(api):
  api.gclient.set_config('gyp')

  api.bot_update.ensure_checkout()

  with api.step.context({'cwd': api.path['checkout']}):
    api.python('run tests',
               api.path['checkout'].join('gyptest.py'), ['-a'])


def GenTests(api):
  yield(api.test('fake_test') +
        api.properties.generic(mastername='fake_mastername',
                               buildername='fake_buildername'))

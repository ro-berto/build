# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

DEPS = [
  'bot_update',
  'file',
  'gclient',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'test_utils',
]

def RunSteps(api):
  api.gclient.set_config('dart')
  api.bot_update.ensure_checkout(force=True)
  api.gclient.runhooks()
  api.python('build dart',
             api.path['checkout'].join('tools', 'build.py'),
             args= ['-mrelease', 'runtime'],
             cwd=api.path['checkout'])
  api.python('test vm',
             api.path['checkout'].join('tools', 'test.py'),
             args= ['-mrelease', '-cnone', '-rvm'],
             cwd=api.path['checkout'])

def GenTests(api):
   yield (
      api.test('linux64') + api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart.FYI'))

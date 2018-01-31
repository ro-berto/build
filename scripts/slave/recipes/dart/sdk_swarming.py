# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

DEPS = [
  'dart',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python'
]

PROPERTIES = {
  'buildername': Property(help="Should end in -[channel]"),
}

def RunSteps(api, buildername):
  _, _, system, channel = buildername.split('-')
  assert system in ['mac', 'linux', 'windows']
  assert channel in ['be', 'dev', 'stable', 'try']

  try:
    api.dart.checkout(clobber=True)

    with api.context(cwd=api.path['checkout'],
                   env={'BUILDBOT_BUILDERNAME':buildername}):
      api.dart.build(['--mode=release', '--arch=ia32', 'create_sdk'])
      api.dart.build(['--mode=release', '--arch=x64', 'create_sdk'])

      if system == 'linux':
        api.python('generate API docs',
            api.path['checkout'].join('tools', 'bots', 'dart_sdk.py'),
            args=['api_docs'])
  finally:
    api.dart.kill_tasks()

def GenTests(api):
  yield (
    api.test('dart-sdk-linux-be') + api.platform('linux', 64) +
    api.properties.generic(mastername='client.dart',
                           buildername='dart-sdk-linux-be'))
  yield (
    api.test('dart-sdk-windows-dev') + api.platform('win', 32) +
    api.properties.generic(mastername='client.dart',
                           buildername='dart-sdk-windows-dev'))
  yield (
    api.test('dart-sdk-mac-try') + api.platform('mac', 64) +
    api.properties.generic(mastername='client.dart',
                           buildername='dart-sdk-mac-try'))

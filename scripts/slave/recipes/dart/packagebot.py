# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'test_utils',
]

PROPERTIES = {
    'target': Property(help='the package to check out and test'),
    'repo': Property(help='the repository URL where the package is located'),
    'project': Property(help='the changesource that triggered this build'),
  }

def RunSteps(api, target, repo, project):
  api.gclient.set_config('dart')
  s = api.gclient.c.solutions[0]
  # package-bots is checked out in two locations:
  #   package-bots and dart/third_party/package-bots.
  s.name = 'package-bots'
  s.url = 'https://dart.googlesource.com/package-bots.git'
  s.custom_deps = {
    'dart/third_party/pkg/%s' % target: repo,
    'dart/third_party/package-bots':
      'https://dart.googlesource.com/package-bots.git'}
  if project != 'package-bots':
    s.revision = 'HEAD'

  api.path.c.dynamic_paths['tools'] = None
  api.path.c.dynamic_paths['dart'] = None
  api.bot_update.ensure_checkout()
  api.path['dart'] = api.path['start_dir'].join('dart')
  api.path['tools'] = api.path['start_dir'].join('dart', 'tools')

  api.gclient.runhooks()

  with api.context(cwd=api.path['dart']):
    api.python(
      'taskkill before building',
      api.path['tools'].join('task_kill.py'),
      args=['--kill_browsers=True'],
      ok_ret='any')
    api.python(
      'package_bots annotated steps',
      api.path['dart'].join(
        'third_party', 'package-bots', 'annotated_steps.py'),
      allow_subannotations=True)
    api.python(
      'taskkill after testing',
      api.path['tools'].join('task_kill.py'),
      args=['--kill_browsers=True'],
      ok_ret='any')

def GenTests(api):
  yield (
      api.test('packages-linux-async') + api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart.packages',
        buildername='packages-linux-async',
        revision='a' * 40,
        project='package-bots',
        target='async',
        repo='https://github.com/dart-lang/async.git'))
  yield (
      api.test('packages-windows-intl') + api.platform('win', 32) +
      api.properties.generic(
        mastername='client.dart.packages',
        buildername='packages-windows-intl',
        revision='a' * 40,
        project='args',
        target='intl',
        repo='https://github.com/dart-lang/intl.git'))

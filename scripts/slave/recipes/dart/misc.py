# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

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

def RunSteps(api):
  builder_name = api.properties.get('buildername')
  builder_fragments = builder_name.split('-')
  assert len(builder_fragments) > 2
  builder = builder_fragments[0]
  system = builder_fragments[1]
  assert system in ['linux', 'mac', 'win']
  assert system == api.platform.name
  channel = builder_fragments[-1]
  assert channel in ['be', 'dev', 'stable', 'integration']

  api.gclient.set_config('dart')
  if builder == 'androidvm':
    api.gclient.c.target_os.add('android')
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')

  api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    api.python('taskkill before building',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True'],
               ok_ret='any')

  scripts = {'dart2jsdumpinfo': 'dart2js_dump_info',
             'pub': 'pub',
             'debianpackage': 'linux_distribution_support',
             'androidvm': 'android',
             'versionchecker': 'version_checker'}
  assert builder in scripts
  script = scripts[builder]
  # TODO(mkroghj) iterate over all scripts, to get result.log from
  # each step
  api.python('%s script' % script,
      api.path['checkout'].join('tools', 'bots','%s.py' % script),
      allow_subannotations=True)

  with api.context(cwd=api.path['checkout']):
    api.python('taskkill after testing',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True'],
               ok_ret='any')

def GenTests(api):
   yield (
      api.test('androidvm-linux-be') +
      api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='androidvm-linux-be',
        revision='a' * 40))
   yield (
      api.test('pub-win-dev') + api.platform('win', 32) +
      api.properties.generic(
        mastername='client.dart',
        buildername='pub-win-dev',
        revision='a' * 40))

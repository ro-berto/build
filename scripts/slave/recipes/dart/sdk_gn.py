# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

def RunSteps(api):
  builder_name = api.properties.get('buildername')
  builder_fragments = builder_name.split('-')
  assert len(builder_fragments) == 5
  assert builder_fragments[0] == 'sdk'
  assert builder_fragments[1] == 'gn'
  system = builder_fragments[2]
  assert system in ['linux', 'mac', 'win']
  mode = builder_fragments[3]
  assert mode == 'release'
  channel = builder_fragments[4]
  assert channel in ['be', 'dev', 'stable', 'integration']

  api.gclient.set_config('dart')
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')

  api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    with api.step.defer_results():
      api.python('taskkill before building',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=['--kill_browsers=True'],
                 ok_ret='any')
      build_args = ['-mrelease', 'runtime', 'create_sdk']
      api.python('gn build dart',
                 api.path['checkout'].join('tools', 'bots', 'gn_build.py'),
                 args=build_args)

    with api.step.defer_results():
      api.python('gn build tests',
                 api.path['checkout'].join('tools', 'bots', 'gn_tests.py'),
                 args=['-mrelease'])

      api.python('taskkill after testing',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=['--kill_browsers=True'],
                 ok_ret='any')

def GenTests(api):
   yield (
      api.test('sdk-gn-linux-release-be') +
      api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='sdk-gn-linux-release-be',
        revision='a' * 40))

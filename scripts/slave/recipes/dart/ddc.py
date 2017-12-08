# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'dart',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]

TARGETS = [
  'language_2',
  'corelib_2',
  'lib_2',
  'lib_strong',
]

def test(api, system, name, args):
  if system == 'linux':
    xvfb_cmd = [
      '/usr/bin/xvfb-run', '-a', '--server-args=-screen 0 1024x768x24',
      'python', '-u', './tools/test.py'
    ]
    api.step(name, xvfb_cmd + args)
  else:
    api.python(name, api.path['checkout'].join('tools', 'test.py'), args)
  api.dart.read_result_file('read results of %s' % name, 'result.log')

def RunSteps(api):
  builder_name = api.properties.get('buildername')
  builder_fragments = builder_name.split('-')
  assert len(builder_fragments) == 4
  assert builder_fragments[0] == 'ddc'
  system = builder_fragments[1]
  assert system in ['linux', 'mac', 'win']
  mode = builder_fragments[2]
  assert mode == 'release'
  channel = builder_fragments[3]
  assert channel in ['be', 'dev', 'stable', 'integration']

  api.gclient.set_config('dart')
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    with api.step.defer_results():
      build_args = ['-mrelease', 'dart2js_bot', 'dartdevc_test']
      with api.context(env_prefixes={'PATH':[api.depot_tools.root]}):
        api.dart.kill_tasks()
        api.python("build dart",
                   api.path['checkout'].join('tools', 'build.py'),
                   args=build_args)

    with api.step.defer_results():
      test_args = [
        '-m%s' % mode,
        '--checked',
        '--progress=buildbot',
        '--report',
        '--strong',
        '--time',
        '--use-sdk',
        '--write-result-log',
      ]
      test(api, system, 'ddc tests',
          test_args + ['-cdartdevc', '-rchrome'] + TARGETS)
      test(api, system, 'ddc kernel tests',
          test_args + ['-rchrome', '-cdartdevk', 'language_2'])
      api.dart.kill_tasks()

def GenTests(api):
   yield (
      api.test('ddc-linux-release-be') +
      api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='ddc-linux-release-be',
        revision='hash_of_revision'))

   yield (
      api.test('ddc-mac-release-dev') +
      api.platform('mac', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='ddc-mac-release-dev',
        revision='hash_of_revision'))

   yield (
      api.test('ddc-win-release-dev') +
      api.platform('win', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='ddc-win-release-dev',
        revision='hash_of_revision'))

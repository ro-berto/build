# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'dart',
  'depot_tools/depot_tools',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'test_utils',
]

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
  assert channel in ['be', 'dev', 'stable', 'integration', 'try']

  api.dart.checkout(channel)

  build_args = ['-mrelease', 'dart2js_bot']
  api.dart.build(build_args)

  with api.context(cwd=api.path['checkout'],
                   env_prefixes={'PATH':[api.depot_tools.root]},
                   env={'BUILDBOT_BUILDERNAME':builder_name}):

    with api.step.defer_results():
      api.python('ddc tests',
                 api.path['checkout'].join('tools', 'bots', 'ddc_tests.py'),
                 args=[])
      api.dart.read_result_file('read results of ddc tests', 'result.log');
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
      api.test('ddc-linux-release-try') +
      api.platform('linux', 64) +
      api.properties.generic(
        mastername='luci.dart.try',
        buildername='ddc-linux-release-try',
        revision='hash_of_revision'))

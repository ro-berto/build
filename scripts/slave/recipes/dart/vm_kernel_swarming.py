# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

DEPS = [
  'dart',
  'depot_tools/depot_tools',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

def RunSteps(api):
  buildername = api.properties.get('buildername')
  builder_fragments = buildername.split('-')
  assert builder_fragments[0] == 'vm'
  assert builder_fragments[1] == 'kernel'
  system = builder_fragments[2]
  assert system in ['linux', 'mac']
  mode = builder_fragments[3]
  assert mode in ['debug', 'release']
  arch = builder_fragments[4]
  assert arch == 'x64'
  channel = builder_fragments[5]
  assert channel in ['be', 'dev', 'stable', 'try']

  test_args = ['-rvm',
               '-m%s' % mode,
               '--arch=%s' % arch,
               '--progress=line',
               '--report',
               '--time',
               '--use-sdk',
               '--write-debug-log',
               '--write-test-outcome-log',
               '--copy-coredumps']
  if mode == 'debug':
    test_args.append('--vm-options=--no-enable-malloc-hooks')

  api.dart.checkout(channel)

  # TODO(athom) This used to be runtime instead of create_sdk, which is correct?
  build_args = ['-m%s' % mode, '--arch=%s' % arch, 'create_sdk', 'runtime_kernel']
  isolate_hash = api.dart.build(build_args, 'dart_tests_extended')

  with api.context(cwd=api.path['checkout'],
                   env_prefixes={'PATH':[api.depot_tools.root]}):

    with api.step.defer_results():
      front_end_args = ['pkg/front_end', '-cnone', '--checked']
      front_end_args.extend(test_args)
      api.python('front-end tests',
                 api.path['checkout'].join('tools', 'test.py'),
                 args=front_end_args)

      test_args.extend(['--append_logs', '-cdartk'])
      test_args = ['./tools/test.py'] + test_args
      api.dart.shard('vm_tests', isolate_hash, test_args)
      api.dart.kill_tasks()
      api.step('debug log', ['cat', '.debug.log'])

def GenTests(api):
   yield (
      api.test('vm-kernel-mac-release-x64-be') +
      api.platform('mac', 64) +
      api.properties.generic(mastername='client.dart.internal',
                             buildername='vm-kernel-mac-release-x64-be') +
      api.properties(shards='3'))
   yield (
      api.test('vm-kernel-linux-debug-x64-try') +
      api.platform('linux', 64) +
      api.properties.generic(
          mastername='luci.dart.try',
          buildername='vm-kernel-linux-debug-x64-try') +
      api.properties(shards='6'))

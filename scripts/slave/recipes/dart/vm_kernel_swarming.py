# Copyright 2015 The Chromium Authors. All rights reserved.
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
               '--builder-tag=swarming',
               '--progress=line',
               '--report',
               '--time',
               '--write-debug-log',
               '--write-result-log',
               '--write-test-outcome-log',
               '--copy-coredumps']
  if mode == 'debug':
    test_args.append('--vm-options=--no-enable-malloc-hooks')

  api.dart.checkout()

  build_args = ['-m%s' % mode, '--arch=%s' % arch, 'create_sdk', 'runtime_kernel']
  isolate_hash = api.dart.build(build_args, 'dart_tests_extended')

  with api.context(cwd=api.path['checkout']):
    with api.depot_tools.on_path():
      with api.step.defer_results():
        front_end_args = ['pkg/front_end', '-cnone', '--checked', '--timeout=120']
        front_end_args.extend(test_args)
        test_args.extend(['--append_logs', '-cdartk'])

        shard_test_args = (['./tools/test.py',
                           '--use-sdk',
                           '--exclude-suite=samples,service,standalone,vm,language_2,corelib_2,lib_2,standalone_2']
                           + test_args)
        tasks = api.dart.shard('vm_tests', isolate_hash, shard_test_args)

        strong_test_args = (['./tools/test.py', '--strong', '--use-sdk',
                           'language_2', 'corelib_2', 'lib_2', 'standalone_2']
                           + test_args)
        tasks = api.dart.shard('vm_strong_tests', isolate_hash, strong_test_args)

        api.python('front-end tests',
                   api.path['checkout'].join('tools', 'test.py'),
                   args=front_end_args)
        api.dart.read_result_file('read results of front-end tests',
                                  'result.log')

        api.python('samples, service, standalone, and vm tests',
                   api.path['checkout'].join('tools', 'test.py'),
                   args=test_args + ['samples', 'service', 'standalone', 'vm'])
        api.dart.read_result_file('read results of samples, service, standalone, and vm tests',
                                  'result.log')

        api.dart.collect(tasks.get_result())

        api.dart.kill_tasks()
        api.step('debug log', ['cat', '.debug.log'])

def GenTests(api):
   yield (
      api.test('vm-kernel-mac-release-x64-be') +
      api.platform('mac', 64) +
      api.properties.generic(mastername='client.dart.internal',
                             buildername='vm-kernel-mac-release-x64-be') +
      api.properties(shards='1'))
   yield (
      api.test('vm-kernel-linux-debug-x64-try') +
      api.platform('linux', 64) +
      api.properties.generic(
          mastername='luci.dart.try',
          buildername='vm-kernel-linux-debug-x64-try') +
      api.properties(shards='3'))

# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

DEPS = [
    'dart',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
]

builders = {
  # This is used by recipe coverage tests, not by any actual master.
  'test-coverage': {
    'mode': 'release',
    'target_arch': 'x64',
    'clobber': True
  },
  'test-coverage-win': {
    'mode': 'release',
    'target_arch': 'x64',
    'clobber': True
  },
}

for platform in ['linux', 'mac']:
  for arch in ['x64']:
    for mode in ['debug', 'release']:
      for checked in ['-checked', '']:
        extra_args = []
        if mode == 'debug':
          extra_args += ['--vm-options=--no-enable-malloc-hooks']
        if checked:
          extra_args += ['--checked']

        builders['vm-kernel-%s-%s-%s%s' % (platform, mode, arch, checked)] = {
          'mode': mode,
          'target_arch': arch,
          'build_args': ['runtime_kernel'],
          'test_args': ['-cdartk', '-rvm'] + extra_args,
          'archive_core_dumps': True,
        }

        builders['vm-kernel-precomp%s-%s-%s-%s'
            % (checked, platform, mode, arch)] = {
          'mode': mode,
          'target_arch': arch,
          'build_args': (['runtime_kernel',
                          'dart_bootstrap',
                          'dart_precompiled_runtime']),
          'test_args': ['-cdartkp', '-rdart_precompiled'] + extra_args,
          'archive_core_dumps': True,
        }

def RunSteps(api):
  api.gclient.set_config('dart')

  # TODO(whesse/kustermann): We should find out if this is necessary (and if so
  # why).  (see https://github.com/dart-lang/sdk/issues/27028)
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')
  raw_buildername = api.properties.get('buildername')

  shard_match = re.match(r'^(.+?)(-([0-9]+)-([0-9]+))?(-(be|dev|stable))?$',
                         raw_buildername)
  buildername = raw_buildername
  shard_args = []
  if shard_match:
    buildername = shard_match.group(1)
    if shard_match.group(2):
      shard_index = int(shard_match.group(3))
      shard_count = int(shard_match.group(4))
      shard_args.append('--shard=%d' % shard_index)
      shard_args.append('--shards=%d' % shard_count)

  b = builders[buildername]

  with api.context(cwd=api.path['checkout']):
    if b.get('clobber', False):
        api.python('clobber',
                   api.path['tools'].join('clean_output_directory.py'))

  api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    api.python('taskkill before building',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True'],
               ok_ret='any')

    build_args = ['-m%s' % b['mode'], '--arch=%s' % b['target_arch'], 'runtime']
    build_args.extend(b.get('build_args', []))
    api.python('build dart',
               api.path['checkout'].join('tools', 'build.py'),
               args=build_args)

    with api.step.defer_results():
      test_args = ['-m%s' % b['mode'],
                   '--arch=%s' % b['target_arch'],
                   '--progress=line',
                   '--report',
                   '--time',
                   '--write-debug-log',
                   '--write-result-log',
                   '--write-test-outcome-log']
      if b.get('archive_core_dumps', False):
        test_args.append('--copy-coredumps')
      test_args.extend(shard_args)
      test_args.extend(b.get('test_args', []))

      non_strong_args = (test_args +
              ['--exclude-suite=language_2,corelib_2,lib_2,standalone_2'])
      api.python('vm tests',
                 api.path['checkout'].join('tools', 'test.py'),
                 args=non_strong_args)
      api.dart.read_result_file('read results of vm tests', 'result.log')

      test_args.append('--append_logs')
      strong_args = (test_args +
              ['--strong', 'language_2', 'corelib_2', 'lib_2', 'standalone_2'])
      api.python('vm strong tests',
                 api.path['checkout'].join('tools', 'test.py'),
                 args=strong_args)
      api.dart.read_result_file('read results of vm strong tests', 'result.log')

      api.python('taskkill after testing',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=['--kill_browsers=True'])
      if api.platform.name == 'win':
        api.step('debug log',
                 ['cmd.exe', '/c', 'type', '.debug.log'])
      else:
        api.step('debug log',
                 ['cat', '.debug.log'])


def GenTests(api):
   yield (
      api.test('vm-kernel-linux-debug-x64') +
      api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart.internal',
                             buildername='vm-kernel-linux-debug-x64'))
   yield (
      api.test('vm-kernel-precomp-linux-debug-x64-be') +
      api.platform('linux', 64) +
      api.properties.generic(
          mastername='client.dart.internal',
          buildername='vm-kernel-precomp-linux-debug-x64-be'))
   yield (
      api.test('vm-kernel-precomp-linux-debug-x64-1-4-be') +
      api.platform('linux', 64) +
      api.properties.generic(
          mastername='client.dart.internal',
          buildername='vm-kernel-precomp-linux-debug-x64-1-4-be'))
   yield (
      api.test('test-coverage') +
      api.platform('linux', 32) +
      api.properties.generic(mastername='client.dart.internal',
                             buildername='test-coverage'))
   yield (
      api.test('test-coverage-win') +
      api.platform('win', 64) +
      api.properties.generic(mastername='client.dart.internal',
                             buildername='test-coverage-win'))

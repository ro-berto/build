# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
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
}

transformer_args = []
general_test_args = ['co19', 'language', 'dill']

for platform in ['linux']:
  for arch in ['x64']:
    for mode in ['debug', 'release']:
      builders['vm-kernel-%s-%s-%s' % (platform, mode, arch)] = {
        'mode': mode,
        'target_arch': arch,
        'build_args': [],
        'test_args': ['-cdartk', '-rvm'] + general_test_args,
      }
      builders['vm-kernel-precomp-%s-%s-%s' % (platform, mode, arch)] = {
        'mode': mode,
        'target_arch': arch,
        'build_args': (['dart_bootstrap',
                        'dart_precompiled_runtime']),
        'test_args': ['-cdartkp', '-rdart_precompiled'] + general_test_args,
      }

def RunSteps(api):
  api.gclient.set_config('dart')

  # TODO(whesse/kustermann): We should find out if this is necessary (and if so
  # why).  (see https://github.com/dart-lang/sdk/issues/27028)
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')
  raw_buildername = api.properties.get('buildername')

  shard_match = re.match(r'^(.+)-([0-9]+)-([0-9]+)(-(be|dev|stable))?$',
                         raw_buildername)
  buildername = raw_buildername
  shard_args = []
  if shard_match:
    buildername = shard_match.group(1)
    shard_index = int(shard_match.group(2))
    shard_count = int(shard_match.group(3))
    shard_args.append('--shard=%d' % shard_index)
    shard_args.append('--shards=%d' % shard_count)

  b = builders[buildername]

  if b.get('clobber', False):
      api.python('clobber',
                 api.path['tools'].join('clean_output_directory.py'),
                 cwd=api.path['checkout'])

  api.gclient.runhooks()

  api.python('taskkill before building',
             api.path['checkout'].join('tools', 'task_kill.py'),
             args=['--kill_browsers=True'],
             cwd=api.path['checkout'],
             ok_ret='any')

  build_args = ['-m%s' % b['mode'], '--arch=%s' % b['target_arch'], 'runtime']
  build_args.extend(b.get('build_args', []))
  api.python('build dart',
             api.path['checkout'].join('tools', 'build.py'),
             args=build_args,
             cwd=api.path['checkout'])

  with api.step.defer_results():
    test_args = ['-m%s' % b['mode'],
                 '--arch=%s' % b['target_arch'],
                 '--progress=line',
                 '--report',
                 '--time',
                 '--failure-summary',
                 '--write-debug-log',
                 '--write-test-outcome-log',
                 '--copy-coredumps',
                 '--exclude-suite=pkg']
    test_args.extend(shard_args)
    test_args.extend(b.get('test_args', []))
    api.python('vm tests',
               api.path['checkout'].join('tools', 'test.py'),
               args=test_args,
               cwd=api.path['checkout'])

    api.python('taskkill after testing',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True'],
               cwd=api.path['checkout'])

def GenTests(api):
   yield (
      api.test('vm-kernel-linux-debug-x64') +
      api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart.internal',
                             buildername='vm-kernel-linux-debug-x64'))
   yield (
      api.test('vm-kernel-precomp-linux-debug-x64') +
      api.platform('linux', 64) +
      api.properties.generic(
          mastername='client.dart.internal',
          buildername='vm-kernel-precomp-linux-debug-x64-be'))
   yield (
      api.test('test-coverage') +
      api.platform('linux', 32) +
      api.properties.generic(mastername='client.dart.internal',
                             buildername='test-coverage'))

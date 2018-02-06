# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

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
    'test_utils',
]

asan64 = {
  'DART_USE_ASAN': '1',
  'ASAN_OPTIONS': 'handle_segv=0:detect_stack_use_after_return=1',
  'ASAN_SYMBOLIZER_PATH': 'buildtools/toolchain/clang+llvm-x86_64-linux/bin/llvm-symbolizer',
}
asan32 = {
  'DART_USE_ASAN': '1',
  'ASAN_OPTIONS': 'handle_segv=0:detect_stack_use_after_return=0',
  'ASAN_SYMBOLIZER_PATH': 'buildtools/toolchain/clang+llvm-x86_64-linux/bin/llvm-symbolizer',
}
linux_asan_env = {
  'x64': asan64,
  'ia32': asan32,
}
windows_env = {'LOGONSERVER': '\\\\AD1',
}
default_envs = {
  'linux': {},
  'mac': {},
  'win': windows_env,
}

builders = {
  # This is used by recipe coverage tests, not by any actual master.
  'test-coverage-win': {
    'mode': 'release',
    'target_arch': 'x64',
    'env': default_envs['win'],
    'checked': True},
}

for platform in ['linux', 'mac', 'win']:
  for arch in ['x64', 'ia32']:
    for mode in ['debug', 'release']:
      builders['vm-%s-%s-%s' % (platform, mode, arch)] = {
        'mode': mode,
        'target_arch': arch,
        'env': default_envs[platform],
        'checked': True,
        'archive_core_dumps': True,
      }
    builders['vm-%s-product-%s' % (platform, arch)] = {
      'mode': 'product',
      'target_arch': arch,
      'env': default_envs[platform],
      'archive_core_dumps': True,
    }

for arch in ['simarm', 'simarm64']:
  for mode in ['debug', 'release']:
    builders['vm-linux-%s-%s' % (mode, arch)] = {
      'mode': mode,
      'target_arch': arch,
      'env': {},
      'checked': True,
      'archive_core_dumps': True,
    }

for arch in ['simdbc64']:
  for mode in ['debug', 'release']:
    builders['vm-mac-%s-%s' % (mode, arch)] = {
      'mode': mode,
      'target_arch': arch,
      'env': {},
      'checked': True,
    }
    builders['vm-mac-%s-%s-reload' % (mode, arch)] = {
      'mode': mode,
      'target_arch': arch,
      'env': {},
      'checked': True,
      'test_args': ['--hot-reload'],
    }

for arch in ['x64', 'ia32']:
  asan = builders['vm-linux-release-%s' % arch].copy()
  asan_args = ['--builder-tag=asan', '--timeout=240']
  asan_args.extend(asan.get('test_args', []))
  asan['test_args'] = asan_args
  asan['env'] = linux_asan_env[arch]
  builders['vm-linux-release-%s-asan' % arch] = asan

  opt = builders['vm-linux-release-%s' % arch].copy()
  opt_args = ['--vm-options=--optimization-counter-threshold=5']
  opt_args.extend(opt.get('test_args', []))
  opt['test_args'] = opt_args
  builders['vm-linux-release-%s-optcounter-threshold' % arch] = opt

for mode in ['debug', 'release', 'product']:
  builders['app-linux-%s-x64' % mode] = {
    'mode': mode,
    'target_arch': 'x64',
    'env': default_envs['linux'],
    'test_args': ['-capp_jit'],
    'archive_core_dumps': True,
  }
  builders['precomp-linux-%s-x64' % mode] = {
    'mode': mode,
    'target_arch': 'x64',
    'env': default_envs['linux'],
    'test_args': ['-cprecompiler', '-rdart_precompiled'],
    'build_args': ['runtime_precompiled'],
    'archive_core_dumps': True,
  }
  for arch in ['x64', 'simdbc64']:
    builders['vm-linux-%s-%s-reload' % (mode, arch)] = {
      'mode': mode,
      'target_arch': arch,
      'env': default_envs['linux'],
      'checked': True,
      'test_args': ['--hot-reload'],
      'archive_core_dumps': True,
    }
    builders['vm-linux-%s-%s-reload-rollback' % (mode, arch)] = {
      'mode': mode,
      'target_arch': arch,
      'env': default_envs['linux'],
      'checked': True,
      'test_args': ['--hot-reload-rollback'],
      'archive_core_dumps': True,
    }


def RunSteps(api):
  buildername = str(api.properties.get('buildername')) # Convert from unicode.
  (buildername, _, channel) = buildername.rpartition('-')
  assert channel in ['be', 'dev', 'stable', 'integration', 'try']
  shard_match = re.match(r'^(.+?)-([0-9]+)-([0-9]+)$', buildername)
  shard_args = []
  if shard_match:
    buildername = shard_match.group(1)
    shard_index = int(shard_match.group(2))
    shard_count = int(shard_match.group(3))
    shard_args.append('--shard=%d' % shard_index)
    shard_args.append('--shards=%d' % shard_count)
  b = builders[buildername]

  api.gclient.set_config('dart')
  if channel == 'try':
    api.gclient.c.solutions[0].url = 'https://dart.googlesource.com/sdk.git'

  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    with api.context(cwd=api.path['checkout']):
      api.python('clobber',
                 api.path['tools'].join('clean_output_directory.py'))

  with api.context(env=b['env']):
    api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    api.dart.kill_tasks()

    build_args = ['-m%s' % b['mode'], '--arch=%s' % b['target_arch'], 'runtime']
    build_args.extend(b.get('build_args', []))
    with api.context(env=b['env']):
      with api.depot_tools.on_path():
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
      if channel == 'try':
        test_args.append('--builder-tag=swarming')
      test_args.extend(b.get('test_args', []))
      test_args.extend(shard_args)
      with api.context(env=b['env']):
        api.python('vm tests',
                   api.path['checkout'].join('tools', 'test.py'),
                   args=test_args)
        api.dart.read_result_file('read results of vm tests', 'result.log')
      if b.get('checked', False):
        test_args.extend(['--checked', '--append_logs'])
        with api.context(env=b['env']):
          api.python('checked vm tests',
                     api.path['checkout'].join('tools','test.py'),
                     args=test_args)
          api.dart.read_result_file('read results of checked vm tests',
                                    'result.log')

      api.dart.kill_tasks()
      api.dart.read_debug_log()

def GenTests(api):
   yield (
      api.test('vm-linux-release-x64-asan-be') + api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart',
                             buildername='vm-linux-release-x64-asan-be'))
   yield (
      api.test('test-coverage') + api.platform('win', 64) +
      api.properties.generic(mastername='client.dart',
                             buildername='test-coverage-win-be',
                             clobber=''))
   yield (
      api.test('precomp-linux-debug-x64-2-3') + api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart',
                             buildername='precomp-linux-debug-x64-2-3-be'))
   yield (
      api.test('vm-linux-debug-x64-try') + api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart',
                             buildername='vm-linux-debug-x64-try'))

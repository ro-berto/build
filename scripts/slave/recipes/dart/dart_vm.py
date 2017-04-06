# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'file',
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
  'ASAN_SYMBOLIZER_PATH': 'third_party/clang/linux/bin/llvm-symbolizer',
}
asan32 = {
  'DART_USE_ASAN': '1',
  'ASAN_OPTIONS': 'handle_segv=0:detect_stack_use_after_return=0',
  'ASAN_SYMBOLIZER_PATH': 'third_party/clang/linux/bin/llvm-symbolizer',
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
        'archive_core_dumps': (platform == 'linux' or platform == 'win'),
      }
    builders['vm-%s-product-%s' % (platform, arch)] = {
      'mode': 'product',
      'target_arch': arch,
      'env': default_envs[platform],
      'test_args': ['--builder-tag=no_ipv6'],
      'archive_core_dumps': (platform == 'linux' or platform == 'win'),
    }

for arch in ['simmips', 'simarm', 'simarm64']:
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

builders['vm-win-debug-ia32-russian'] = builders['vm-win-debug-ia32']

for mode in ['debug', 'release', 'product']:
  builders['app-linux-%s-x64' % mode] = {
    'mode': mode,
    'target_arch': 'x64',
    'env': default_envs['linux'],
    'test_args': ['-capp_jit',
                  '--builder-tag=no_ipv6'],
    'archive_core_dumps': True,
  }
  builders['precomp-linux-%s-x64' % mode] = {
    'mode': mode,
    'target_arch': 'x64',
    'env': default_envs['linux'],
    'test_args': ['-cprecompiler', '-rdart_precompiled', '--use-blobs',
                  '--builder-tag=no_ipv6'],
    'build_args': ['runtime_precompiled'],
    'archive_core_dumps': True,
  }
  for arch in ['x64', 'simdbc64']:
    builders['vm-linux-%s-%s-reload' % (mode, arch)] = {
      'mode': mode,
      'target_arch': arch,
      'env': default_envs['linux'],
      'checked': True,
      'test_args': ['--hot-reload',
                    '--builder-tag=no_ipv6'],
      'archive_core_dumps': True,
    }
    builders['vm-linux-%s-%s-reload-rollback' % (mode, arch)] = {
      'mode': mode,
      'target_arch': arch,
      'env': default_envs['linux'],
      'checked': True,
      'test_args': ['--hot-reload-rollback',
                    '--builder-tag=no_ipv6'],
      'archive_core_dumps': True,
    }


def RunSteps(api):
  api.gclient.set_config('dart')
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')
  buildername = str(api.properties.get('buildername')) # Convert from unicode.
  (buildername, _, channel) = buildername.rpartition('-')
  assert channel in ['be', 'dev', 'stable', 'integration']
  b = builders[buildername]

  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    with api.step.context({'cwd': api.path['checkout']}):
      api.python('clobber',
                 api.path['tools'].join('clean_output_directory.py'))

  with api.step.context({'env': b['env'].copy()}):
    api.gclient.runhooks()

  with api.step.context({'cwd': api.path['checkout']}):
    api.python('taskkill before building',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True'])

    build_args = ['-m%s' % b['mode'], '--arch=%s' % b['target_arch'], 'runtime']
    build_args.extend(b.get('build_args', []))
    with api.step.context({'env': b['env']}):
      api.python('build dart',
                 api.path['checkout'].join('tools', 'build.py'),
                 args=build_args)

    with api.step.defer_results():
      test_args = ['-m%s' % b['mode'],
                   '--arch=%s' % b['target_arch'],
                   '--progress=line',
                   '--report',
                   '--time',
                   '--failure-summary',
                   '--write-debug-log',
                   '--write-test-outcome-log']
      if b.get('archive_core_dumps', False):
        test_args.append('--copy-coredumps')
      test_args.extend(b.get('test_args', []))
      with api.step.context({'env': b['env']}):
        api.python('vm tests',
                   api.path['checkout'].join('tools', 'test.py'),
                   args=test_args)
      if b.get('checked', False):
        test_args.extend(['--checked', '--append_logs'])
        with api.step.context({'env': b['env']}):
          api.python('checked vm tests',
                     api.path['checkout'].join('tools', 'test.py'),
                     args=test_args)

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
      api.test('vm-linux-release-x64-asan-be') + api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart',
                             buildername='vm-linux-release-x64-asan-be'))
   yield (
      api.test('test-coverage') + api.platform('win', 64) +
      api.properties.generic(mastername='client.dart',
                             buildername='test-coverage-win-be',
                             clobber=''))
   yield (
      api.test('precomp-linux-debug-x64') + api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart',
                             buildername='precomp-linux-debug-x64-be'))

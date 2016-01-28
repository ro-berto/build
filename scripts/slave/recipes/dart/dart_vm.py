# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property

DEPS = [
  'depot_tools/bot_update',
  'file',
  'depot_tools/gclient',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'test_utils',
]

linux_clang_env = {'CC': 'third_party/clang/linux/bin/clang',
                   'CXX': 'third_party/clang/linux/bin/clang++'}
clang_asan = 'third_party/clang/linux/bin/clang++ -fsanitize=address -fPIC'
linux_asan_env_64 = {'CXX': clang_asan,
                     'ASAN_OPTIONS':
                     'handle_segv=0:detect_stack_use_after_return=1'}
linux_asan_env_32 = {'CXX': clang_asan,
                     'ASAN_OPTIONS':
                     'handle_segv=0:detect_stack_use_after_return=0'}

builders = {
  'vm-linux-release-ia32-asan': {
    'mode': 'release',
    'target_arch': 'ia32',
    'env': linux_asan_env_32},
  'vm-linux-release-x64-asan': {
    'mode': 'release',
    'target_arch': 'x64',
    'env': linux_asan_env_64},
  'vm-linux-debug-ia32': {
    'mode': 'release',
    'target_arch': 'ia32',
    'test_args': ['--exclude-suite=pkg'],
    'env': linux_clang_env},
  'vm-linux-debug-x64': {
    'mode': 'release',
    'target_arch': 'x64',
    'test_args': ['--exclude-suite=pkg'],
    'env': linux_clang_env},
  'test-coverage': {
    'mode': 'release',
    'target_arch': 'x64',
    'env': linux_clang_env,
    'clobber': True},
}

def RunSteps(api):
  api.gclient.set_config('dart')
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout(force=True)
  api.path['tools'] = api.path['checkout'].join('tools')
  buildername = api.properties.get('buildername')
  (buildername, _, channel) = buildername.rpartition('-')
  assert( channel in ['be', 'dev', 'stable', 'integration'] )
  buildername = buildername.replace('-recipe', '')
  b = builders[buildername]


  if b.get('clobber', False):
      api.python('clobber',
                 api.path['tools'].join('clean_output_directory.py'),
                 cwd=api.path['checkout'])

  api.gclient.runhooks()

  api.python('taskkill before building',
             api.path['checkout'].join('tools', 'task_kill.py'),
             args=['--kill_browsers=True'],
             cwd=api.path['checkout'])

  build_args = ['-m%s' % b['mode'], '--arch=%s' % b['target_arch'], 'runtime']
  api.python('build dart',
             api.path['checkout'].join('tools', 'build.py'),
             args=build_args,
             cwd=api.path['checkout'],
             env=b['env'])

  test_args = ['-m%s' % b['mode'],
               '--arch=%s' % b['target_arch'],
               '--progress=line',
               '--report',
               '--time',
               '--failure-summary',
               '--write-debug-log',
               '--write-test-outcome-log',
               '--copy-coredumps']
  test_args.extend(b.get('test_args', []))
  api.python('test vm',
             api.path['checkout'].join('tools', 'test.py'),
             args=test_args,
             cwd=api.path['checkout'])
  test_args.append('--checked')
  api.python('test vm',
             api.path['checkout'].join('tools', 'test.py'),
             args=test_args,
             cwd=api.path['checkout'])

  api.python('taskkill after testing',
             api.path['checkout'].join('tools', 'task_kill.py'),
             args=['--kill_browsers=True'],
             cwd=api.path['checkout'])

def GenTests(api):
   yield (
      api.test('vm-linux-release-x64-asan-be') + api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart',
                             buildername='vm-linux-release-x64-asan-be'))
   yield (
      api.test('test-coverage') + api.platform('linux', 32) +
      api.properties.generic(mastername='client.dart',
                             buildername='test-coverage-be'))

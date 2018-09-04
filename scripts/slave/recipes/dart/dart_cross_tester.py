# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'dart',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/gsutil',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'test_utils',
]

GCS_BUCKET = 'gs://dart-cross-compiled-binaries'

builders = {
  'target-arm-vm-linux-release': {
    'mode': 'release',
    'target_arch': 'arm'},
  'target-arm64-vm-linux-release': {
    'mode': 'release',
    'target_arch': 'arm64'},
}

def tarball_name(arch, mode, revision):
  return 'cross_build_%s_%s_%s.tar.bz2' % (arch, mode, revision)

def RunSteps(api):
  api.gclient.set_config('dart')
  api.path.c.dynamic_paths['tools'] = None
  revision = api.properties['revision']
  api.bot_update.ensure_checkout()

  api.path['tools'] = api.path['checkout'].join('tools')
  buildername = str(api.properties.get('buildername')) # Convert from unicode.
  (buildername, _, channel) = buildername.rpartition('-')
  assert channel in ['be', 'dev', 'stable', 'integration']
  buildername = buildername.replace('-recipe', '')
  b = builders[buildername]

  with api.context(cwd=api.path['checkout']):
    api.python('clobber',
               api.path['tools'].join('clean_output_directory.py'),
               ok_ret='any')
  with api.context(env={'DART_USE_GYP': '1'}):
    api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    tarball = tarball_name(b['target_arch'], b['mode'], revision)
    uri = "%s/%s" % (GCS_BUCKET, tarball)
    api.gsutil(['cp', uri, tarball], name='download tarball')
    api.step('untar tarball', ['tar', '-xjf', tarball])

    with api.step.defer_results():
      test_args = ['--mode=%s' % b['mode'],
                   '--arch=%s' % b['target_arch'],
                   '--compiler=dartk',
                   '--progress=line',
                   '--report',
                   '--time',
                   '--write-debug-log',
                   '--write-result-log',
                   '--write-test-outcome-log']
      test_args.extend(b.get('test_args', []))
      api.python('vm tests',
                 api.path['tools'].join('test.py'),
                 args=test_args)
      api.dart.read_result_file('read results of vm tests', 'result.log')
      api.step('debug log', ['cat', '.debug.log'])
      api.step('delete tarball', ['rm', tarball])
      api.python('clobber',
                 api.path['tools'].join('clean_output_directory.py'))


def GenTests(api):
  yield (
    api.test('target-arm-vm-linux-release') +
    api.platform('linux', 64) +
    api.properties.generic(mastername='client.dart',
                           buildername='target-arm-vm-linux-release-be',
                           revision='a' * 40))

# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'file',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'test_utils',
  'trigger',
]

GCS_BUCKET = 'gs://dart-cross-compiled-binaries'

builders = {
  'cross-arm-vm-linux-release': {
    'mode': 'release',
    'target_arch': 'arm'},
  'cross-arm64-vm-linux-release': {
    'mode': 'release',
    'target_arch': 'arm64'},
  'test-coverage': {
    'mode': 'release',
    'target_arch': 'x64',
    'clobber': True},
}

def tarball_name(arch, mode, revision):
  return 'cross_build_%s_%s_%s.tar.bz2' % (arch, mode, revision)

def RunSteps(api):
  api.gclient.set_config('dart')
  api.path.c.dynamic_paths['tools'] = None
  update_step = api.bot_update.ensure_checkout()
  revision = update_step.json.output['fixed_revisions']['sdk']

  api.path['tools'] = api.path['checkout'].join('tools')
  buildername = api.properties.get('buildername')
  (buildername, _, channel) = buildername.rpartition('-')
  assert channel in ['be', 'dev', 'stable', 'integration']
  buildername = buildername.replace('-recipe', '')
  b = builders[buildername]

  if b.get('clobber', False):
    with api.context(cwd=api.path['checkout']):
      api.python('clobber',
                 api.path['tools'].join('clean_output_directory.py'))

  api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    build_args = ['-m%s' % b['mode'], '--arch=%s' % b['target_arch'], 'runtime']
    api.python('build dart',
               api.path['checkout'].join('tools', 'build.py'),
               args=build_args)
    tarball = tarball_name(b['target_arch'], b['mode'], revision)
    api.step('create tarball',
             ['tar', '-cjf', tarball, '--exclude=**/obj',
               '--exclude=**/obj.host', '--exclude=**/obj.target',
               '--exclude=**/*analyzer*', 'out/'])

    uri = "%s/%s" % (GCS_BUCKET, tarball)
    api.gsutil(['cp', '-a', 'public-read', tarball, uri],
               name='upoad tarball')

  # Trigger slaves
  target_builder = buildername.replace('cross-', 'target-')
  trigger_spec = [{
    'builder_name': '%s-%s' % (target_builder, channel)
  }]
  api.trigger(*trigger_spec)


def GenTests(api):
  yield (
    api.test('cross-arm-vm-linux-release-recipe') +
    api.platform('linux', 64) +
    api.properties.generic(mastername='client.dart',
                           buildername='cross-arm-vm-linux-release-recipe-be',
                           revision='abcd1234efef5656'))
  yield (
    api.test('clobber-coverage') +
    api.platform('linux', 64) +
    api.properties.generic(mastername='client.dart',
                           buildername='test-coverage-stable',
                           revision='abcd1234efef5656'))

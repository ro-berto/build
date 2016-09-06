# Copyright 2016 The Chromium Authors. All rights reserved.
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
]

def RunSteps(api):
  builder_name = api.properties.get('buildername')
  gyp_defines = ['component=static_library', 'linux_strip_binary']
  if '-win-' in builder_name:
    gyp_defines.append('fastbuild=1')
  if '-ia32-' in builder_name:
    gyp_defines.append('target_arch=ia32')
  if '-x64-' in builder_name:
    gyp_defines.append('target_arch=x64')
  api.gclient.set_config('dart') # There is no 'dartium' configuration
  s = api.gclient.c.solutions[0]
  s.name = 'src/dart'
  s.url = ('https://chromium.googlesource.com/external/github.com/' +
              'dart-lang/sdk.git')
  s.deps_file = 'tools/deps/dartium.deps/DEPS'
  s.managed = False
  s.revision = api.properties.get('revision')
  api.bot_update.ensure_checkout(force=True)

  api.gclient.runhooks(env={'GYP_GENERATORS': 'ninja',
                            'GYP_DEFINES': ' '.join(gyp_defines)})
  api.gclient.c.got_revision_mapping.pop('src', None)
  api.gclient.c.got_revision_mapping['src/dart'] = 'got_revision'

  # gclient api sets Path('[CHECKOUT]') to build/src/dart.  We prefer build/src.
  api.path['checkout'] = api.path['slave_build'].join('src')

  with api.step.defer_results():
    api.python(
      'build dartium',
      api.path['checkout'].join('dart', 'tools', 'dartium', 'build.py'),
      args=['--mode=Release'],
      cwd=api.path['checkout'],
      env={'GYP_GENERATORS': 'ninja',
           'GYP_DEFINES': ' '.join(gyp_defines)})
    api.python(
      'annotated steps',
      api.path['checkout'].join(
        'dart', 'tools', 'dartium', 'buildbot_annotated_steps.py'),
      cwd=api.path['checkout'])
    if '-inc-' not in builder_name:
      api.file.rmtree('clobber', 'out', cwd=api.path['checkout'])

def GenTests(api):
  yield (
    api.test('dartium-win-ia32-be') +
    api.properties.generic(
      mastername='client.dart',
      buildername='dartium-win-ia32-be',
      revision='12345') +
    api.platform('win', 32))
  yield (
    api.test('dartium-linux-x64-dev') +
    api.properties.generic(
      mastername='client.dart',
      buildername='dartium-linux-x64-dev',
      revision='12345') +
    api.platform('linux', 64))
  yield (
    api.test('dartium-mac-ia32-inc-stable') +
    api.properties.generic(
      mastername='client.dart',
      buildername='dartium-mac-ia32-inc-stable',
      revision='12345') +
    api.platform('mac', 32))

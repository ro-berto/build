# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter

DEPS = [
  'dart',
  'depot_tools/git',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'zip',
]

def RunSteps(api):
  version = api.properties.get('version')
  channel = 'dev' if '-dev' in version else 'stable'

  api.git.checkout(url='https://github.com/dart-lang/dart_docker.git')

  env = {
    'DOCKER_CONFIG': api.path['cleanup'].join('.docker'),
  }
  with api.context(cwd=api.path['cleanup'], env=env):
    sdk = 'channels/%s/release/%s/sdk/dartsdk-linux-x64-release.zip' % (
        channel, version)
    sdk_zip = api.path['cleanup'].join('dartsdk-linux-x64-release.zip')
    api.gsutil.download('dart-archive', sdk, sdk_zip, name='download dart sdk')
    api.zip.unzip('unzip sdk', sdk_zip, api.path['cleanup'].join('sdk'))

    dockerhub_key = api.dart.get_secret('dockerhub')
    login = [
      '/bin/bash',
      '-c',
      '/usr/bin/docker login --username dartbot -p $(cat %s)' % dockerhub_key]
    api.step('docker login', login)

  env_prefixes = {
    'PATH': [api.path['cleanup'].join('sdk').join('dart-sdk').join('bin')],
  }
  build_push = (api.path['start_dir']
      .join('dart_docker')
      .join('build_push.sh'))
  with api.context(env=env, env_prefixes=env_prefixes):
    api.step('build and push', [build_push, 'google', version])

def GenTests(api):
  yield (
    api.test('release') +
    api.properties.generic(
      version='1.24.3')
  )
  yield (
    api.test('dev') +
    api.properties.generic(version='2.0.0-dev.51.0') +
    api.post_process(Filter('gsutil download dart sdk'))
  )

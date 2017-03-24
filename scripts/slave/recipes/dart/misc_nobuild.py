# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'test_utils',
  'zip',
]

build_directories= {'linux': 'out/ReleaseX64',
                    'win': 'out/ReleaseX64',
                    'mac': 'xcodebuild/ReleaseX64'}

def sdk_url(channel, platform, arch, mode, revision):
  platforms = {
      'linux': 'linux',
      'win': 'windows',
      'mac': 'macos',
  }
  platform = platforms[platform]
  # The paths here come from dart-lang/sdk/tools/bots/bot_utils.py
  return ('gs://dart-archive/channels/%s/raw/hash/%s/sdk/dartsdk-%s-%s-%s.zip'
     % (channel, revision, platform, arch, mode))

def RunSteps(api):
  builder_name = api.properties.get('buildername')
  builder_fragments = builder_name.split('-')
  assert len(builder_fragments) > 2
  builder = builder_fragments[0]
  system = builder_fragments[1]
  assert system in ['linux', 'mac', 'win']
  assert system == api.platform.name
  channel = builder_fragments[-1]
  assert channel in ['be', 'dev', 'stable', 'integration']

  api.gclient.set_config('dart')
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')
  revision = api.properties['revision']

  api.gclient.runhooks()

  with api.step.context({'cwd': api.path['checkout']}):
    api.python('taskkill before building',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True'],
               ok_ret='any')
    zipfile = api.path.abspath(api.path['checkout'].join('sdk.zip'))
    url = sdk_url(channel, api.platform.name, 'x64', 'release', revision)
    api.gsutil(['cp', url, zipfile], name='Download sdk')
  build_dir = api.path['checkout'].join(build_directories[api.platform.name])
  build_dir = api.path.abspath(build_dir)
  api.file.makedirs('Create build directory', build_dir)
  api.file.rmtree('Clean build directory', build_dir)
  api.zip.unzip('Unzip sdk', zipfile, build_dir)

  if builder == 'analyze':
    with api.step.defer_results():
      with api.step.context({'cwd': api.path['checkout']}):
        dartanalyzer_name = 'dartanalyzer'
        if api.platform.name == 'win':
          dartanalyzer_name = 'dartanalyzer.bat'
        dartanalyzer = api.path['checkout'].join(
          build_directories[api.platform.name],
          'dart-sdk', 'bin', dartanalyzer_name)
        api.step('analyze analysis_server',
                 [dartanalyzer, "--no-hints", "pkg/analysis_server"])
        api.step('analyze analyzer',
                 [dartanalyzer, "--no-hints", "pkg/analyzer"])
        api.step('analyze analyzer_plugin',
                 [dartanalyzer, "--no-hints", "pkg/analyzer_plugin"])

  with api.step.context({'cwd': api.path['checkout']}):
    api.python('taskkill after testing',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True'],
               ok_ret='any')

def GenTests(api):
   yield (
      api.test('analyze-linux-be') +
      api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart.fyi',
        buildername='analyze-linux-be',
        revision='hash_of_revision'))
   yield (
      api.test('analyze-win-dev') + api.platform('win', 32) +
      api.properties.generic(
        mastername='client.dart',
        buildername='analyze-win-dev',
        revision='hash_of_revision'))

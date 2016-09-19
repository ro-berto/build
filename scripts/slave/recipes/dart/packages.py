# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'file',
  'gsutil',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'test_utils',
  'zip',
]

build_directories = {'linux': 'out/ReleaseX64',
                     'win': 'out/ReleaseX64',
                     'mac': 'xcodebuild/ReleaseX64'}

is_first_test_step = True
def RunTests(api, test_args, test_specs):
  for test_spec in test_specs:
    args = []
    args.extend(test_args)
    global is_first_test_step
    if is_first_test_step:
      is_first_test_step = False
    else:
      args.append('--append_logs')
    args.extend(test_spec['tests'])
    api.python(test_spec['name'],
               api.path['checkout'].join('tools', 'test.py'),
               args=args,
               cwd=api.path['checkout'])

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
  # Buildername should be like 'analyzer-linux-debug-dev'.
  builder_name = api.properties.get('buildername')
  builder_fragments = builder_name.split('-')
  assert len(builder_fragments) > 3
  builder_type = builder_fragments[0]
  assert builder_type in ['analyzer', 'pkg']
  system = builder_fragments[1]
  assert system in ['linux', 'mac10.11', 'win7', 'win8', 'win10']
  mode = builder_fragments[2]
  assert mode in ['debug', 'release']
  channel = builder_fragments[-1]
  assert channel in ['be', 'dev', 'stable', 'integration']

  api.gclient.set_config('dart', GIT_MODE=True)
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')
  revision = api.properties['revision']

  api.gclient.runhooks()

  api.python('taskkill before building',
             api.path['checkout'].join('tools', 'task_kill.py'),
             args=['--kill_browsers=True'],
             cwd=api.path['checkout'],
             ok_ret='any'
             )
  with api.step.defer_results():
    zipfile = api.path.abspath(api.path['checkout'].join('sdk.zip'))
    url = sdk_url(channel, api.platform.name, 'x64', mode, revision)
    api.gsutil(['cp', url, zipfile], name='Download sdk',
               cwd=api.path['checkout'])
    build_dir = api.path['checkout'].join(build_directories[api.platform.name])
    build_dir = api.path.abspath(build_dir)
    api.file.makedirs('Create build directory', build_dir)
    api.file.rmtree('Clean build directory', build_dir)
    api.zip.unzip('Unzip sdk', zipfile, build_dir)

  with api.step.defer_results():
    test_args = ['--mode=%s' % mode,
                 '--arch=x64',
                 '--use-sdk',
                 '--compiler=none',
                 '--runtime=vm',
                 '--checked',
                 '--progress=buildbot',
                 '-v',
                 '--report',
                 '--time',
                 '--failure-summary',
                 '--write-debug-log',
                 '--write-test-outcome-log',
                 '--copy-coredumps']
    if system in ['win7', 'win8', 'win10']:
      test_args.append('--builder-tag=%s' % system)

    if builder_type == 'analyzer':
      test_specs = [
        {'name': 'analyzer unit tests',
         'tests': ['pkg/analyzer']},
        {'name': 'analysis server unit tests',
         'tests': ['pkg/analysis_server']},
        {'name': 'analyzer_cli unit tests',
         'tests': ['pkg/analyzer_cli']},
        {'name': 'get dependencies - public',
         'tests': ['--use-public-packages', 'pkgbuild/pkg/analy']},
        {'name': 'get dependencies - repo',
         'tests': ['--use-repository-packages', 'pkgbuild/pkg/analy']},
      ]
    else:
      assert builder_type == 'pkg'
      test_specs = [
        {'name': 'package unit tests',
         'tests': ['pkg']},
        {'name': 'get dependencies - public',
         'tests': ['--use-public-packages', 'pkgbuild']},
        {'name': 'get dependencies - repo',
         'tests': ['--use-repository-packages', 'pkgbuild']},
      ]
    RunTests(api, tuple(test_args), test_specs)

    # TODO(whesse): Add archive coredumps step from dart_factory.py.
    api.python('taskkill after testing',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True'],
               cwd=api.path['checkout'],
               ok_ret='any')
    # TODO(whesse): Upload the logs to cloud storage, put a link to them
    # in the step presentation.
    if system in ['linux', 'mac10.11']:
      api.step('debug log',
               ['cat', '.debug.log'],
               cwd=api.path['checkout'])

def GenTests(api):
   yield (
      api.test('analyzer-linux-release-be') +
      api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='analyzer-linux-release-be',
        revision='hash_of_revision'))
   yield (
      api.test('analyzer-win7-debug-dev') + api.platform('win', 32) +
      api.properties.generic(
        mastername='client.dart',
        buildername='analyzer-win7-debug-dev',
        revision='hash_of_revision'))
   yield (
      api.test('pkg-mac10.11-release-be') + api.platform('mac', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='pkg-mac10.11-release-be',
        revision='hash_of_revision'))

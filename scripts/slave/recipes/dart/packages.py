# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'dart',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/file',
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
    with api.context(cwd=api.path['checkout'],
                     env={'PUB_ENVIRONMENT': 'dart_bots'}):
      api.python(test_spec['name'],
                 api.path['checkout'].join('tools', 'test.py'),
                 args=args)
      api.dart.read_result_file('read results of %s' % test_spec['name'],
                                'result.log')


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
  strong = builder_fragments[3] == 'strong'
  channel = builder_fragments[-1]
  assert channel in ['be', 'dev', 'stable', 'integration']

  api.gclient.set_config('dart', GIT_MODE=True)
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')
  revision = api.properties['revision']

  api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    api.python('taskkill before building',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True'],
               ok_ret='any'
               )
  with api.step.defer_results():
    zipfile = api.path.abspath(api.path['checkout'].join('sdk.zip'))
    url = sdk_url(channel, api.platform.name, 'x64', mode, revision)
    with api.context(cwd=api.path['checkout']):
      api.gsutil(['cp', url, zipfile], name='Download sdk')
    build_dir = api.path['checkout'].join(build_directories[api.platform.name])
    build_dir = api.path.abspath(build_dir)
    api.file.ensure_directory('Create build directory', build_dir)
    api.file.rmtree('Clean build directory', build_dir)
    api.zip.unzip('Unzip sdk', zipfile, build_dir)

  with api.step.defer_results():
    if builder_type == 'analyzer':
      test_args = ['--mode=%s' % mode,
                   '--arch=x64',
                   '--use-sdk',
                   '--compiler=dart2analyzer',
                   '--runtime=none',
                   '--progress=buildbot',
                   '--report',
                   '--time',
                   '--write-debug-log',
                   '--write-result-log',
                   '--write-test-outcome-log',
                   '--copy-coredumps']
      test_specs = [
        {'name': 'analyze tests',
         'tests': []},
        {'name': 'analyze pkg tests',
         'tests': ['pkg']},
        {'name': 'analyze tests checked',
         'tests': ['--checked']},
        {'name': 'analyze pkg tests checked',
         'tests': ['--checked', 'pkg']},
      ]
      if strong:
        test_args.append('--strong')
        test_specs.extend([
          {'name': 'analyze strong tests',
           'tests': ['--exclude-suite=co19']},
          {'name': 'analyze strong tests checked',
           'tests': ['--checked', '--exclude-suite=co19']},
          {'name': 'analyze tests preview-dart2',
           'tests': ['--preview-dart-2']},
        ])
      RunTests(api, test_args, test_specs)

    # Run package unit tests
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
                 '--write-debug-log',
                 '--write-result-log',
                 '--write-test-outcome-log']
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
      ]
    else:
      assert builder_type == 'pkg'
      test_specs = [
        {'name': 'package unit tests',
         'tests': ['--timeout=120', 'pkg']},
        {'name': 'third_party/pkg_tested unit tests',
         'tests': ['pkg_tested']},
        {'name': 'pub get dependencies',
         'tests': ['pkgbuild']},
      ]
    RunTests(api, test_args, test_specs)

    with api.context(cwd=api.path['checkout']):
      # TODO(whesse): Add archive coredumps step from dart_factory.py.
      api.python('taskkill after testing',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=['--kill_browsers=True'],
                 ok_ret='any')
      if api.platform.name == 'win':
        api.step('debug log',
                 ['cmd.exe', '/c', 'type', '.debug.log'])
      else:
        api.step('debug log',
                 ['cat', '.debug.log'])

def GenTests(api):
   yield (
      api.test('analyzer-linux-release-strong-be') +
      api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='analyzer-linux-release-strong-be',
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
   yield (
      api.test('pkg-linux-release-stable') + api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='pkg-linux-release-stable',
        revision='hash_of_revision'))

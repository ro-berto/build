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

IsFirstTestStep = True
def RunTests(api, test_args, test_specs):
  for test_spec in test_specs:
    args = []
    args.extend(test_args)
    global IsFirstTestStep
    if IsFirstTestStep:
      IsFirstTestStep = False
    else:
      args.append('--append_logs')
    args.extend(test_spec['tests'])

    with api.context(cwd=api.path['checkout']):
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
  builder_name = str(api.properties.get('buildername')) # Convert from unicode.
  builder_fragments = builder_name.split('-')
  assert len(builder_fragments) > 3
  assert builder_fragments[0] == 'dart2js'
  system = builder_fragments[1]
  assert system in ['win7', 'win8', 'win10']
  runtime = builder_fragments[2]
  assert runtime == 'ie11'
  channel = builder_fragments[-1]
  assert channel in ['be', 'dev', 'stable', 'integration']
  num_shards = int(builder_fragments[-2])
  shard = int(builder_fragments[-3])

  api.gclient.set_config('dart')
  api.path.c.dynamic_paths['tools'] = None
  api.bot_update.ensure_checkout()
  api.path['tools'] = api.path['checkout'].join('tools')
  revision = api.properties['revision']

  api.gclient.runhooks()

  with api.step.defer_results():
    with api.context(cwd=api.path['checkout']):
      api.python('taskkill before building',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=['--kill_browsers=True'],
                 ok_ret='any')
      zipfile = api.path.abspath(api.path['checkout'].join('sdk.zip'))
      url = sdk_url(channel, api.platform.name, 'x64', 'release', revision)
      api.gsutil(['cp', url, zipfile], name='Download sdk')
    build_dir = api.path['checkout'].join(build_directories[api.platform.name])
    build_dir = api.path.abspath(build_dir)
    api.file.ensure_directory('Create build directory', build_dir)
    api.file.rmtree('Clean build directory', build_dir)
    api.zip.unzip('Unzip sdk', zipfile, build_dir)

  with api.step.defer_results():
    # TODO(whesse): Call a script that prints the runtime version.
    test_args = ['--mode=release',
                   '--arch=x64',
                   '--use-sdk',
                   '--compiler=dart2js',
                   '--dart2js-batch',
                   '--runtime=%s' % runtime,
                   '--progress=buildbot',
                   '-v',
                   '--reset-browser-configuration',
                   '--report',
                   '--time',
                   '--write-debug-log',
                   '--write-result-log',
                   '--write-test-outcome-log',
                   '--shards=%s' % num_shards,
                   '--shard=%s' % shard,
                   '--builder-tag=%s' % system,
                   '-j6',
                   '--timeout=120'] # Issue 28955, IE is slow.
    test_specs = [{'name': 'dart2js %s tests' % runtime,
                       'tests': ['html', 'pkg', 'samples']},
                      {'name': 'dart2js %s co19 tests' % runtime,
                       'tests': ['co19']}]

    RunTests(api, test_args, test_specs)

    test_args.append('--fast-startup')
    for spec in test_specs:
      spec['name'] = spec['name'].replace(' tests', '-fast-startup tests')
    RunTests(api, test_args, test_specs)

  with api.context(cwd=api.path['checkout']):
    # TODO(whesse): Add archive coredumps step from dart_factory.py.
    api.python('taskkill after testing',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=['--kill_browsers=True'],
                 ok_ret='any')
    api.step('debug log', ['cmd.exe', '/c', 'type', '.debug.log'])

def GenTests(api):
   yield (
      api.test('dart2js-win7-ie11-dev') + api.platform('win', 32) +
      api.properties.generic(
        mastername='client.dart',
        buildername='dart2js-win7-ie11-3-5-dev',
        revision='hash_of_revision'))

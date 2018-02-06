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


all_runtimes = ['d8', 'jsshell', 'ie9', 'ie10', 'ie11', 'ff',
            'safari', 'chrome', 'chromeff',
            'ie10chrome', 'ie11ff']

multiple_runtimes = {'chromeff': ['chrome', 'ff'],
                     'ie10chrome': ['ie10', 'chrome'],
                     'ie11ff': ['ie11', 'ff']}
all_options = {'hostchecked': '--host-checked',
               'minified': '--minified',
               'cps': '--cps-ir',
               'csp': '--csp'}
build_directories = {'linux': 'out/ReleaseX64',
                    'win': 'out/ReleaseX64',
                    'mac': 'xcodebuild/ReleaseX64'}

IsFirstTestStep = True
def RunTests(api, test_args, test_specs, use_xvfb=False):
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
      if use_xvfb:
        xvfb_cmd = ['xvfb-run', '-a', '--server-args=-screen 0 1024x768x24']
        xvfb_cmd.extend(['python', '-u', './tools/test.py'])
        xvfb_cmd.extend(args)
        api.step(test_spec['name'], xvfb_cmd)
        api.dart.read_result_file('read results of %s' % test_spec['name'],
                                  'result.log')
      else:
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
  assert system in ['linux', 'mac10.11', 'win7', 'win8', 'win10']
  runtime = builder_fragments[2]
  assert runtime in all_runtimes
  channel = builder_fragments[-1]
  assert channel in ['be', 'dev', 'stable', 'integration']
  try:
    num_shards = int(builder_fragments[-2])
    shard = int(builder_fragments[-3])
    sharded = True
    options_end = - 3
  except ValueError:
    sharded = False
    options_end = - 1
  options = builder_fragments[3:options_end]
  for option in options:
    assert all_options.has_key(option)

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
    runtimes = multiple_runtimes.get(runtime, [runtime])
    for runtime in runtimes:
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
                   '--write-test-outcome-log']
      for option in options:
        test_args.append(all_options[option])
      if sharded:
        test_args.extend(['--shards=%s' % num_shards, '--shard=%s' % shard])

      if system in ['win7', 'win8', 'win10']:
        test_args.append('--builder-tag=%s' % system)

      if runtime in ['ie10', 'ie11']:
        test_args.extend(['-j6', '--timeout=120'])  # Issue 28955, IE is slow.
        test_specs = [{'name': 'dart2js %s tests' % runtime,
                       'tests': ['html', 'pkg', 'samples']},
                      {'name': 'dart2js %s co19 tests' % runtime,
                       'tests': ['co19']}]
      else:
        test_specs = [
          {'name': 'dart2js-%s tests' % runtime,
           'tests': ['--exclude-suite=observatory_ui,co19']},
          {'name': 'dart2js-%s-package tests' % runtime,
           'tests': ['pkg']},
          {'name': 'dart2js-%s-observatory_ui tests' % runtime,
           'tests': ['observatory_ui']},
          {'name': 'dart2js-%s-extra tests' % runtime,
           'tests': ['dart2js_extra', 'dart2js_native']},
          {'name': 'dart2js-%s-co19 tests' % runtime,
           'tests': ['co19']},
        ]

      needs_xvfb = (runtime in ['dartium', 'chrome', 'ff'] and
                    system == 'linux')
      RunTests(api, test_args, test_specs, use_xvfb=needs_xvfb)

      if runtime == 'd8':
        kernel_test_args = test_args + ['--dart2js-with-kernel']
        kernel_test_specs = [{
            'name': 'dart2js-with-kernel-d8 tests',
            'tests': ['language', 'corelib', 'dart2js_extra', 'dart2js_native']
        }]
        RunTests(api, kernel_test_args, kernel_test_specs, use_xvfb=needs_xvfb)
        kernel_strong_test_args = test_args + ['--strong', '--dart2js-with-kernel']
        kernel_strong_test_specs = [{
            'name': 'dart2js-with-kernel-strong-d8 tests',
            'tests': ['language_2', 'corelib_2']
        }]
        RunTests(api, kernel_strong_test_args, kernel_strong_test_specs,
                use_xvfb=needs_xvfb)

      test_args.append('--fast-startup')
      for spec in test_specs:
        spec['name'] = spec['name'].replace(' tests', '-fast-startup tests')
      RunTests(api, test_args, test_specs, use_xvfb=needs_xvfb)

      if runtime in ['d8']:
        test_args.append('--checked')
        for spec in test_specs:
          spec['name'] = spec['name'].replace(' tests', '-checked tests')
        RunTests(api, test_args, test_specs, use_xvfb=needs_xvfb)

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
      api.test('dart2js-linux-jsshell-hostchecked-csp-3-5-be') +
      api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='dart2js-linux-jsshell-hostchecked-csp-3-5-be',
        revision='hash_of_revision'))
   yield (
      api.test('dart2js-win7-ie10-dev') + api.platform('win', 32) +
      api.properties.generic(
        mastername='client.dart',
        buildername='dart2js-win7-ie10-dev',
        revision='hash_of_revision'))
   yield (
      api.test('dart2js-linux-chrome-be') + api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='dart2js-linux-chrome-93-105-dev',
        revision='hash_of_revision'))
   yield (
      api.test('dart2js-linux-d8-be') + api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='dart2js-linux-d8-1-4-be',
        revision='hash_of_revision'))
   yield (
      api.test('dart2js-mac10.11-safari-1-3-be') + api.platform('mac', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='dart2js-mac10.11-safari-1-3-be',
        revision='hash_of_revision'))

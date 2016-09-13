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


all_runtimes = ['d8', 'jsshell', 'ie9', 'ie10', 'ie11', 'ff',
            'safari', 'chrome', 'safarimobilesim', 'drt', 'chromeff',
            'ie10chrome', 'ie11ff']

multiple_runtimes = {'chromeff': ['chrome', 'ff'],
                     'ie10chrome': ['ie10', 'chrome'],
                     'ie11ff': ['ie11', 'ff']}
all_options = {'hostchecked': '--host-checked',
               'minified': '--minified',
               'cps': '--cps-ir',
               'csp': '--csp'}
build_directories= {'linux': 'out/ReleaseX64',
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

    if use_xvfb:
      xvfb_cmd = ['xvfb-run', '-a', '--server-args=-screen 0 1024x768x24']
      xvfb_cmd.extend(['python', '-u', './tools/test.py'])
      xvfb_cmd.extend(args)
      api.step(test_spec['name'], xvfb_cmd, cwd=api.path['checkout'])
    else:
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
  global IsFirstTestStep
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
    api.python('taskkill before building',
               api.path['checkout'].join('tools', 'task_kill.py'),
               args=['--kill_browsers=True'],
               cwd=api.path['checkout'],
               ok_ret='any')
    zipfile = api.path.abspath(api.path['checkout'].join('sdk.zip'))
    url = sdk_url(channel, api.platform.name, 'x64', 'release', revision)
    api.gsutil(['cp', url, zipfile], name='Download sdk',
               cwd=api.path['checkout'])
    build_dir = api.path['checkout'].join(build_directories[api.platform.name])
    build_dir = api.path.abspath(build_dir)
    api.file.makedirs('Create build directory', build_dir)
    api.file.rmtree('Clean build directory', build_dir)
    api.zip.unzip('Unzip sdk', zipfile, build_dir)

  # Build only the package links. Once we remove this target, build nothing.
  if api.platform.name == 'mac':
    api.file.remove('Mark package links as out-of-date',
      api.path.abspath(api.path['checkout'].join(
        'xcodebuild', 'DerivedSources', 'ReleaseX64', 'packages.stamp')),
      ok_ret='any')
  build_args = ['-mrelease', '--arch=x64', 'packages']
  api.python('build dart',
             api.path['checkout'].join('tools', 'build.py'),
             args=build_args,
             cwd=api.path['checkout'])

  with api.step.defer_results():
    # Special hard-coded steps with compiler=none, run on selected runtimes
    if runtime == 'jsshell' and system == 'linux' and sharded:
      IsFirstTestStep = False
      api.python('dart2js unit tests',
                 api.path['checkout'].join('tools', 'test.py'),
                 args=["--mode=release", "--compiler=none", "--runtime=vm",
                       "--arch=x64", "--time", "--use-sdk", "--report",
                       "--write-debug-log", "--write-test-outcome-log",
                       "--progress=buildbot", "-v",
                       "--reset-browser-configuration",
                       "--shards=%s" % num_shards, "--shard=%s" % shard,
                       "--checked", "dart2js"],
                 cwd=api.path['checkout'])

    # Standard test steps, run on all runtimes.
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
                   '--failure-summary',
                   '--write-debug-log',
                   '--write-test-outcome-log',
                   '--copy-coredumps']
      for option in options:
        test_args.append(all_options[option])
      if sharded:
        test_args.extend(['--shards=%s' % num_shards, '--shard=%s' % shard])

      if system in ['win7', 'win8', 'win10']:
        test_args.append('--builder-tag=%s' % system)

      if runtime in ['ie10', 'ie11']:
        test_specs = [{'name': 'dart2js %s tests' % runtime,
                  'tests': ['html', 'pkg', 'samples', 'co19']}]
      else:
        test_specs = [
          {'name': 'dart2js %s tests' % runtime, 'tests': []},
          {'name': 'dart2js %s extra tests' % runtime,
           'tests': ['dart2js_extra', 'dart2js_native']},
        ]

      needs_xvfb = (runtime in ['drt', 'dartium', 'chrome', 'ff'] and
                    system == 'linux')
      RunTests(api, test_args, test_specs, use_xvfb=needs_xvfb)
      test_args.append('--fast-startup')
      for spec in test_specs:
        spec['name'] = spec['name'].replace(' tests', ' fast-startup tests')
      RunTests(api, test_args, test_specs, use_xvfb=needs_xvfb)
      if runtime in ['d8', 'drt']:
        test_args.append('--checked')
        for spec in test_specs:
          spec['name'] = spec['name'].replace(' tests', ' checked tests')
        RunTests(api, test_args, test_specs, use_xvfb=needs_xvfb)

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
      api.test('dart2js-linux-drt-be') + api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='dart2js-linux-drt-93-105-dev',
        revision='hash_of_revision'))
   yield (
      api.test('dart2js-mac10.11-safari-1-3-be') + api.platform('mac', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='dart2js-mac10.11-safari-1-3-be',
        revision='hash_of_revision'))

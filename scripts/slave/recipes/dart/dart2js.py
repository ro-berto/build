# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'dart',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'recipe_engine/context',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'test_utils',
]


all_runtimes = ['none', 'd8', 'ie9', 'ie10', 'ie11', 'ff',
            'safari', 'chrome', 'safarimobilesim', 'drt', 'chromeff',
            'ie10chrome', 'ie11ff']

multiple_runtimes = {'chromeff': ['chrome', 'ff'],
                     'ie10chrome': ['ie10', 'chrome'],
                     'ie11ff': ['ie11', 'ff']}
all_options = {'hostchecked': '--host-checked',
               'minified': '--minified',
               'cps': '--cps-ir',
               'csp': '--csp',
               'unittest': '',  # unittest is handled specially.
               'debug': ''} # debug is handled specially.

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
      with api.depot_tools.on_path():
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
  assert channel in ['be', 'dev', 'stable', 'integration', 'try']
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
  mode = 'debug' if 'debug' in options else 'release'
  api.gclient.set_config('dart')
  if channel == 'try':
    api.gclient.c.solutions[0].url = 'https://dart.googlesource.com/sdk.git'

  api.bot_update.ensure_checkout()
  api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    with api.depot_tools.on_path():
      api.python('taskkill before building',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=['--kill_browsers=True'])

      build_args = ['-m%s' % mode, '--arch=ia32', 'dart2js_bot']
      if 'unittest' in options:
        build_args.append('compile_dart2js_platform')
      api.python('build dart',
                 api.path['checkout'].join('tools', 'build.py'),
                 args=build_args)

  with api.step.defer_results():
    # Standard test steps, run on all runtimes.
    runtimes = multiple_runtimes.get(runtime, [runtime])
    for runtime in runtimes:
      test_args = ['--mode=%s' % mode,
                   '--arch=ia32',
                   '--compiler=dart2js',
                   '--dart2js-batch',
                   '--no-preview-dart-2',
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
        if all_options[option] != '':
          test_args.append(all_options[option])
      if sharded:
        test_args.extend(['--shards=%s' % num_shards, '--shard=%s' % shard])

      if system in ['win7', 'win8', 'win10']:
        test_args.append('--builder-tag=%s' % system)

      if runtime in ['ie10', 'ie11']:
        test_specs = [{'name': 'dart2js-%s tests' % runtime,
                       'tests': ['html', 'pkg', 'samples']},
                      {'name': 'dart2js-%s-co19 tests' % runtime,
                       'tests': ['co19']}]
      else:
        test_specs = [
          {'name': 'dart2js-%s tests' % runtime,
           'tests': ['--exclude-suite=observatory_ui,co19']},
          {'name': 'dart2js-%s-package tests' % runtime,
           'tests': ['pkg']},
          {'name': 'dart2js-%s-observatory-ui tests' % runtime,
           'tests': ['observatory_ui']},
          {'name': 'dart2js-%s-extra tests' % runtime,
           'tests': ['dart2js_extra', 'dart2js_native']},
          {'name': 'dart2js-%s-co19 tests' % runtime,
           'tests': ['co19']},
        ]

      needs_xvfb = (runtime in ['drt', 'dartium', 'chrome', 'ff'] and
                    system == 'linux')
      RunTests(api, test_args, test_specs, use_xvfb=needs_xvfb)
      if runtime in ['d8', 'drt']:
        test_args.append('--checked')
        for spec in test_specs:
          spec['name'] = spec['name'].replace(' tests', '-checked tests')
        RunTests(api, test_args, test_specs, use_xvfb=needs_xvfb)

    if 'unittest' in options:
      with api.context(cwd=api.path['checkout']):
        api.python('dart2js-unit tests',
                   api.path['checkout'].join('tools', 'test.py'),
                   args=["--mode=%s" % mode, "--compiler=none", "--runtime=vm",
                         "--arch=ia32", "--time", "--report",
                         "--no-preview-dart-2",
                         "--write-debug-log",
                         "--write-result-log",
                         "--write-test-outcome-log",
                         "--progress=buildbot", "-v", "--append_logs",
                         "--reset-browser-configuration",
                         "--shards=%s" % num_shards, "--shard=%s" % shard,
                         "--checked", "--timeout=120", "dart2js"])
        api.dart.read_result_file('read results of dart2js-unit tests',
                                  'result.log')


    with api.context(cwd=api.path['checkout']):
      # TODO(whesse): Add archive coredumps step from dart_factory.py.
      api.python('taskkill after testing',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=['--kill_browsers=True'])
      api.dart.read_debug_log()

def GenTests(api):
   yield (
      api.test('dart2js-linux-d8-hostchecked-csp-unittest-3-5-try') +
      api.platform('linux', 64) +
      api.properties.generic(mastername='luci.dart.try',
          buildername='dart2js-linux-d8-hostchecked-csp-unittest-3-5-try'))
   yield (
      api.test('dart2js-win7-ie10-debug-dev') + api.platform('win', 32) +
      api.properties.generic(mastername='client.dart',
                             buildername='dart2js-win7-ie10-debug-dev'))
   yield (
      api.test('dart2js-linux-drt-be') + api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart',
                             buildername='dart2js-linux-drt-93-105-dev'))

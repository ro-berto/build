# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'dart',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'test_utils',
]

all_runtimes = ['none', 'd8', 'jsshell', 'ie9', 'ie10', 'ie11', 'ff',
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

xvfb_cmd = ['/usr/bin/xvfb-run', '-a', '--server-args=-screen 0 1024x768x24']
xvfb_cmd.extend(['python', '-u', './tools/test.py'])

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

    with api.context(cwd=api.path['checkout'],
                     env_prefixes={'PATH':[api.depot_tools.root]}):
      if use_xvfb:
        cmd = xvfb_cmd + args
        api.step(test_spec['name'], cmd)
      else:
        api.python(test_spec['name'],
                   api.path['checkout'].join('tools', 'test.py'),
                   args=args)

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
  options = builder_fragments[3:-1]
  for option in options:
    assert all_options.has_key(option)
  mode = 'debug' if 'debug' in options else 'release'

  api.dart.checkout(channel)

  build_args = ['-m%s' % mode, '--arch=ia32', 'dart2js_bot']
  if 'unittest' in options:
    build_args.append('patched_dart2js_sdk')
  isolate_hash = api.dart.build(build_args, 'dart_tests')

  with api.step.defer_results():
    # Standard test steps, run on all runtimes.
    runtimes = multiple_runtimes.get(runtime, [runtime])
    for runtime in runtimes:
      needs_xvfb = (runtime in ['drt', 'chrome', 'ff'] and
                    system == 'linux')
      command = xvfb_cmd if needs_xvfb else ['./tools/test.py']

      test_args = command + ['-m%s' % mode, '-aia32', '-cdart2js',
                   '--dart2js-batch', '--reset-browser-configuration',
                   '--report', '--time', '--use-sdk', '--progress=buildbot',
                   '-v',
                   '--exclude-suite=observatory_ui,service,co19',
                   '-r%s' % runtime]
      api.dart.shard('dart2js_tests', isolate_hash, test_args)

      test_args = command + ['-m%s' % mode, '-aia32', '-cdart2js', '-r%s' % runtime,
                   '--dart2js-batch', '--reset-browser-configuration',
                   '--report', '--time', '--use-sdk', '--progress=buildbot',
                   '-v',
                   'co19']
      api.dart.shard('dart2js_co19_tests', isolate_hash, test_args)

      test_args = ['--mode=%s' % mode,
                   '--arch=ia32',
                   '--compiler=dart2js',
                   '--dart2js-batch',
                   '--runtime=%s' % runtime,
                   '--progress=buildbot',
                   '-v',
                   '--reset-browser-configuration',
                   '--report',
                   '--time',
                   '--write-debug-log',
                   '--write-test-outcome-log']
      for option in options:
        if all_options[option] != '':
          test_args.append(all_options[option])

      if system in ['win7', 'win8', 'win10']:
        test_args.append('--builder-tag=%s' % system)

      if runtime in ['ie10', 'ie11']:
        test_specs = [{'name': 'dart2js-%s tests' % runtime,
                       'tests': ['html', 'pkg', 'samples']},
                      {'name': 'dart2js-%s-co19 tests' % runtime,
                       'tests': ['co19']}]
      else:
        test_specs = [
          {'name': 'dart2js-%s-package tests' % runtime,
           'tests': ['pkg']},
          {'name': 'dart2js-%s-observatory-ui tests' % runtime,
           'tests': ['observatory_ui']},
          {'name': 'dart2js-%s-extra tests' % runtime,
           'tests': ['dart2js_extra', 'dart2js_native']},
        ]

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
                         "--arch=ia32", "--time", "--use-sdk", "--report",
                         "--write-debug-log", "--write-test-outcome-log",
                         "--progress=buildbot", "-v", "--append_logs",
                         "--reset-browser-configuration",
                         "--checked", "dart2js"])

    with api.context(cwd=api.path['checkout']):
      # TODO(whesse): Add archive coredumps step from dart_factory.py.
      api.dart.kill_tasks()
      if api.platform.name == 'win':
        api.step('debug log',
                 ['cmd.exe', '/c', 'type', '.debug.log'])
      else:
        api.step('debug log',
                 ['cat', '.debug.log'])

def GenTests(api):
   yield (
      api.test('dart2js-linux-d8-hostchecked-csp-unittest-try') +
      api.platform('linux', 64) +
      api.properties.generic(
        mastername='luci.dart.try',
        buildername='dart2js-linux-d8-hostchecked-csp-unittest-try') +
      api.step_data('upload testing isolate',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.properties(shards='3')
   )
   yield (
      api.test('dart2js-win7-ie10-debug-try') + api.platform('win', 32) +
      api.properties.generic(
        mastername='client.dart',
        buildername='dart2js-win7-ie10-debug-try') +
      api.step_data('upload testing isolate',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.properties(shards='6')
   )
   yield (
      api.test('dart2js-linux-drt-try') + api.platform('linux', 64) +
      api.properties.generic(mastername='client.dart',
                             buildername='dart2js-linux-drt-try') +
      api.step_data('upload testing isolate',
                    stdout=api.raw_io.output('test isolate hash')) +
      api.properties(shards='9')
   )

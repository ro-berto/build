# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'dart',
    'depot_tools/depot_tools',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'test_utils',
]

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
      with api.depot_tools.on_path():
        api.python(test_spec['name'],
                   api.path['checkout'].join('tools', 'test.py'),
                   args=args)
        api.dart.read_result_file('read results of %s' % test_spec['name'],
                                  'result.log')


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
  strong = 'strong' in builder_fragments
  hostchecked = 'hostchecked' in builder_fragments
  channel = builder_fragments[-1]
  assert channel in ['be', 'dev', 'stable', 'integration', 'try']

  api.dart.checkout()

  with api.context(cwd=api.path['checkout']):
    with api.depot_tools.on_path():
      api.python('taskkill before building',
                 api.path['checkout'].join('tools', 'task_kill.py'),
                 args=['--kill_browsers=True'],
                 ok_ret='any'
                 )
      build_args = ['-m%s' % mode, '--arch=x64', 'dart2js_bot']
      api.dart.build(build_args=build_args)

  with api.step.defer_results():
    if builder_type == 'analyzer':
      test_args = ['--mode=%s' % mode,
                   '--arch=x64',
                   '--use-sdk' if not hostchecked else '--host-checked',
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
        test_args.extend(['--strong', '--builder-tag=strong'])
        test_specs.extend([
          {'name': 'analyze strong tests',
           'tests': ['language_strong', 'lib_strong', 'corelib_strong']},
          {'name': 'analyze strong tests checked',
           'tests': ['--checked', 'language_strong', 'lib_strong',
                     'corelib_strong']},
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
    if system == 'linux' and builder_type == 'pkg':
      test_args.append('--builder-tag=no_ipv6')

    if builder_type == 'analyzer':
      test_specs = [
        {'name': 'analyzer unit tests',
         'tests': ['pkg/analyzer']},
        {'name': 'analysis server unit tests',
         'tests': ['pkg/analysis_server']},
        {'name': 'analyzer_cli unit tests',
         'tests': ['pkg/analyzer_cli']},
        {'name': 'front end unit tests',
         'tests': ['--timeout=120', 'pkg/front_end']},
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
      if api.platform.is_win:
        api.step('debug log',
                 ['cmd.exe', '/c', 'type', '.debug.log'])
      else:
        api.step('debug log',
                 ['cat', '.debug.log'])

def GenTests(api):
   yield (
      api.test('analyzer-linux-release-strong-hostchecked-try') +
      api.platform('linux', 64) +
      api.properties.generic(
        mastername='luci.dart.try',
        buildername='analyzer-linux-release-strong-hostchecked-try',
        revision='hash_of_revision'))
   yield (
      api.test('analyzer-win7-debug-dev') + api.platform('win', 32) +
      api.properties.generic(
        mastername='client.dart',
        buildername='analyzer-win7-debug-dev',
        revision='hash_of_revision'))
   yield (
      api.test('pkg-mac10.11-release-try') + api.platform('mac', 64) +
      api.properties.generic(
        mastername='luci.dart.try',
        buildername='pkg-mac10.11-release-try',
        revision='hash_of_revision'))
   yield (
      api.test('pkg-linux-release-stable') + api.platform('linux', 64) +
      api.properties.generic(
        mastername='client.dart',
        buildername='pkg-linux-release-stable',
        revision='hash_of_revision'))

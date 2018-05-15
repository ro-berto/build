# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]

def Build(api, config, *targets):
  checkout = api.path['start_dir'].join('src')
  build_dir = checkout.join('out/%s' % config)
  ninja_args = ['ninja', '-C', build_dir]
  ninja_args.extend(targets)
  api.step('build %s' % ' '.join([config] + list(targets)), ninja_args)

def RunGN(api, *args):
  checkout = api.path['start_dir'].join('src')
  gn_cmd = [checkout.join('flutter/tools/gn')]
  gn_cmd.extend(args)
  api.step('gn %s' % ' '.join(args), gn_cmd)

def AnalyzeDartUI(api):
  checkout = api.path['start_dir'].join('src')
  with api.context(cwd=checkout):
    api.step('analyze dart_ui', ['/bin/bash', 'flutter/travis/analyze.sh'])

def BuildLinuxAndroidx86(api):
  for x86_variant in ['x64', 'x86']:
    RunGN(api, '--android', '--android-cpu=' + x86_variant)
    Build(api, 'android_debug_' + x86_variant)

def BuildLinuxAndroidArm(api):
  RunGN(api, '--android')
  Build(api, 'android_debug')
  Build(api, 'android_debug', ':dist')

  # Build and upload engines for the runtime modes that use AOT compilation.
  for runtime_mode in ['profile', 'release']:
    build_output_dir = 'android_' + runtime_mode

    RunGN(api, '--android', '--runtime-mode=' + runtime_mode)
    Build(api, build_output_dir)

def BuildLinux(api):
  RunGN(api)
  Build(api, 'host_debug')

def TestObservatory(api):
  checkout = api.path['start_dir'].join('src')
  flutter_tester_path = checkout.join('out/host_debug/flutter_tester')
  empty_main_path = checkout.join(
      'flutter/shell/testing/observatory/empty_main.dart')
  test_path = checkout.join('flutter/shell/testing/observatory/test.dart')
  test_cmd = ['dart', '--preview-dart-2', test_path, flutter_tester_path,
      empty_main_path]
  with api.context(cwd=checkout):
    api.step('test observatory and service protocol', test_cmd)

def GetCheckout(api):
  src_cfg = api.gclient.make_config()
  src_cfg.target_os = set(['android'])
  src_cfg.revisions = {
    'src/flutter': api.properties.get('rev_engine') or
                   api.properties.get('revision') or 'HEAD',
    'src/third_party/dart': api.properties.get('rev_sdk') or 'HEAD',
    'flutter': api.properties.get('rev_flutter') or 'HEAD',
  }

  soln = src_cfg.solutions.add()
  soln.name = 'src/flutter'
  soln.url = \
      'https://chromium.googlesource.com/external/github.com/flutter/engine'

  soln = src_cfg.solutions.add()
  soln.name = 'flutter'
  soln.url = \
      'https://chromium.googlesource.com/external/github.com/flutter/flutter'

  api.gclient.c = src_cfg
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()

def TestFlutter(api):
  engine_src = api.path['start_dir'].join('src')
  flutter = api.path['start_dir'].join('flutter')
  flutter_cmd = flutter.join('bin/flutter')
  test_args = [
      '--local-engine=host_debug',
      '--local-engine-src-path=%s' % engine_src,
  ]
  test_cmd = [
    'dart', '--preview-dart-2', 'dev/bots/test.dart',
  ]
  api.step('disable flutter analytics', [flutter_cmd, 'config', '--no-analytics'])
  with api.context(cwd=flutter):
    with api.context(cwd=flutter.join('dev/bots')):
      api.step('pub get in dev/bots before flutter test', ['pub', 'get'])
    api.step('flutter update-packages',
             [flutter_cmd, 'update-packages'] + test_args)
    # runs all flutter tests similar to travis as described on this page:
    # https://github.com/flutter/flutter/blob/master/CONTRIBUTING.md
    api.step('flutter test', test_cmd + test_args)

def RunSteps(api):
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmcontents('everything', api.path['start_dir'])
  GetCheckout(api)

  BuildLinux(api)
  checkout = api.path['start_dir'].join('src')
  dart_bin = checkout.join(
      'out', 'host_debug', 'dart-sdk', 'bin')
  env = { 'PATH': api.path.pathsep.join((str(dart_bin), '%(PATH)s')) }

  # The context adds dart-sdk/bin to the path.
  with api.context(env=env):
    with api.step.defer_results():
      AnalyzeDartUI(api)
      TestObservatory(api)
      BuildLinuxAndroidArm(api)
      BuildLinuxAndroidx86(api)
      TestFlutter(api)

def GenTests(api):
  yield (api.test('flutter-engine-linux') + api.platform('linux', 64)
      + api.properties(mastername='client.dart.internal',
            buildername='flutter-engine-linux',
            bot_id='fake-m1', clobber='',
            rev_sdk='foo', rev_engine='bar'))

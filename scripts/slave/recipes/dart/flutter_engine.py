# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'goma',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
]

def Build(api, checkout_dir, config, *targets):
  build_dir = checkout_dir.join('out/%s' % config)
  ninja_cmd = [api.depot_tools.ninja_path, '-j', api.goma.jobs, '-C', build_dir]
  ninja_cmd.extend(targets)
  api.goma.build_with_goma(
    name='build %s' % ' '.join([config] + list(targets)),
    ninja_command=ninja_cmd)

def RunGN(api, checkout_dir, *args):
  gn_cmd = [checkout_dir.join('flutter/tools/gn')]
  gn_cmd.extend(args)
  # Flutter's gn tool needs ninja in the PATH
  with api.depot_tools.on_path():
    api.step('gn %s' % ' '.join(args), gn_cmd)

def AnalyzeDartUI(api, checkout_dir):
  with api.context(cwd=checkout_dir):
    api.step('analyze dart_ui', ['/bin/bash', 'flutter/ci/analyze.sh'])

def TestEngine(api, checkout_dir):
  with api.context(cwd=checkout_dir):
    api.step('test engine', ['/bin/bash', 'flutter/testing/run_tests.sh'])

def BuildLinuxAndroidx86(api, checkout_dir):
  for x86_variant in ['x64', 'x86']:
    RunGN(api, checkout_dir, '--android', '--android-cpu=' + x86_variant)
    Build(api, checkout_dir, 'android_debug_' + x86_variant)

def BuildLinuxAndroidArm(api, checkout_dir):
  RunGN(api, checkout_dir, '--android')
  Build(api, checkout_dir, 'android_debug')
  Build(api, checkout_dir, 'android_debug', ':dist')

  # Build and upload engines for the runtime modes that use AOT compilation.
  for runtime_mode in ['profile', 'release']:
    build_output_dir = 'android_' + runtime_mode

    RunGN(api, checkout_dir, '--android', '--runtime-mode=' + runtime_mode)
    Build(api, checkout_dir, build_output_dir)

def BuildLinux(api, checkout_dir):
  RunGN(api, checkout_dir)
  Build(api, checkout_dir, 'host_debug')
  RunGN(api, checkout_dir, '--unoptimized')
  Build(api, checkout_dir, 'host_debug_unopt')

def TestObservatory(api, checkout_dir):
  flutter_tester_path = checkout_dir.join('out/host_debug/flutter_tester')
  empty_main_path = checkout_dir.join(
      'flutter/shell/testing/observatory/empty_main.dart')
  test_path = checkout_dir.join('flutter/shell/testing/observatory/test.dart')
  test_cmd = ['dart', test_path, flutter_tester_path, empty_main_path]
  with api.context(cwd=checkout_dir):
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

  api.step('3xHEAD Flutter Hooks',
      ['src/third_party/dart/tools/3xhead_flutter_hooks.sh'])

def TestFlutter(api, start_dir, just_built_dart_sdk, just_built_gen):
  engine_src = start_dir.join('src')
  flutter = start_dir.join('flutter')
  flutter_cmd = flutter.join('bin/flutter')
  test_args = [
      '--local-engine=host_debug',
      '--local-engine-src-path=%s' % engine_src,
  ]
  test_cmd = [
    'dart', 'dev/bots/test.dart',
  ]
  api.step('disable flutter analytics', [flutter_cmd, 'config', '--no-analytics'])
  with api.context(cwd=flutter):
    api.step('flutter update-packages',
             [flutter_cmd, 'update-packages'] + test_args)

    # analyze.dart and test.dart have hardcoded references to bin/cache/dart-sdk.
    # So we overwrite bin/cache/dart-sdk and tightly-coupled frontend_server.dart.snapshot
    # with links that point to corresponding entries from [just_built_dart_sdk]
    dart_sdk = flutter.join('bin', 'cache', 'dart-sdk')
    frontend_server = flutter.join(
      'bin', 'cache', 'artifacts', 'engine', 'linux-x64', 'frontend_server.dart.snapshot')

    # In case dart-sdk symlink was left from previous run we need to [remove] it,
    # rather than [rmtree] because rmtree is going to remove symlink target folder.
    # We are not able to use api.file classes for this because there is no
    # support for symlink checks or handling of error condition.
    api.step('cleanup', [
      '/bin/bash', '-c', '\"if [ -L %(s)s ]; then rm %(s)s else rm -rf %(s)s; fi\"' %
      {'s': dart_sdk}])

    api.file.remove('remove downloaded frontend_server snapshot', frontend_server)
    api.file.symlink('make cached dart-sdk point to just built dart sdk', just_built_dart_sdk, dart_sdk)
    api.file.symlink('make frontend_server.dart.snapshot point to just built version',
      just_built_gen.join('frontend_server.dart.snapshot'),
      frontend_server)

    # runs all flutter tests similar to Cirrus as described on this page:
    # https://github.com/flutter/flutter/blob/master/CONTRIBUTING.md
    api.step('flutter analyze', ['dart', 'dev/bots/analyze.dart',
             '--dart-sdk', just_built_dart_sdk
             ], timeout=20*60) # 20 minutes
    api.step('flutter test', test_cmd + test_args, timeout=90*60) # 90 minutes

def RunSteps(api):
  if api.runtime.is_luci:
    start_dir = api.path['cache'].join('builder')
  else:
    start_dir = api.path['start_dir']

  with api.context(cwd=start_dir):
    # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
    if 'clobber' in api.properties:
      api.file.rmcontents('everything', start_dir)
    GetCheckout(api)

  api.goma.ensure_goma()
  with api.context(cwd=start_dir, env={'GOMA_DIR':api.goma.goma_dir}):
    checkout_dir = start_dir.join('src')
    BuildLinux(api, checkout_dir)
    prebuilt_dart_bin = checkout_dir.join('third_party', 'dart', 'tools',
      'sdks', 'dart-sdk', 'bin')
    engine_env = { 'PATH': api.path.pathsep.join((str(prebuilt_dart_bin),
      '%(PATH)s')) }
    just_built_gen = checkout_dir.join('out', 'host_debug', 'gen')
    just_built_dart_sdk = checkout_dir.join('out', 'host_debug', 'dart-sdk')
    flutter_env = {
      'PATH': api.path.pathsep.join((str(just_built_dart_sdk.join('bin')), '%(PATH)s')),
      # Prevent test.dart from using git merge-base to determine a fork point.
      # git merge-base doesn't work without a FETCH_HEAD, which isn't available
      # on the first run of a bot. The builder tests a single revision, so use
      # rev_flutter.
      'TEST_COMMIT_RANGE': api.properties.get('rev_flutter') or 'HEAD'
    }

    with api.step.defer_results():
      # The context adds prebuilt dart-sdk to the path.
      with api.context(env=engine_env):
        AnalyzeDartUI(api, checkout_dir)
        TestEngine(api, checkout_dir)
        TestObservatory(api, checkout_dir)
        BuildLinuxAndroidArm(api, checkout_dir)
        BuildLinuxAndroidx86(api, checkout_dir)
      # The context adds freshly-built engine's dart-sdk to the path.
      with api.context(env=flutter_env):
        TestFlutter(api, start_dir, just_built_dart_sdk, just_built_gen)

def GenTests(api):
  yield (api.test('flutter-engine-linux-buildbot') + api.platform('linux', 64)
      + api.properties(mastername='client.dart.internal',
            buildername='flutter-engine-linux',
            bot_id='fake-m1', clobber='',
            rev_sdk='foo', rev_engine='bar')
      + api.runtime(is_luci=False, is_experimental=False))
  yield (api.test('flutter-engine-linux') + api.platform('linux', 64)
      + api.properties(mastername='client.dart.internal',
            buildername='flutter-engine-linux',
            bot_id='fake-m1', clobber='',
            rev_sdk='foo', rev_engine='bar')
      + api.runtime(is_luci=True, is_experimental=False))

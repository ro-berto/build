# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json


DEPS = [
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'depot_tools/gitiles',
  'goma',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/runtime',
  'recipe_engine/step',
]


COMMITS_JSON = 'commits.json'
ENGINE_REPO = 'external/github.com/flutter/engine'
FLUTTER_REPO = 'external/github.com/flutter/flutter'
SDK_REPO = 'sdk'


def KillTasks(api, checkout_dir, ok_ret='any'):
  """Kills leftover tasks from previous runs or steps."""
  dart_sdk_dir = checkout_dir.join('third_party', 'dart')
  api.python('kill processes',
               dart_sdk_dir.join('tools', 'task_kill.py'),
               ok_ret=ok_ret)


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
  with api.context(cwd=checkout_dir), api.depot_tools.on_path():
    api.step('test engine', ['/bin/bash', 'flutter/testing/run_tests.sh'])


def BuildLinuxAndroidx86(api, checkout_dir):
  for x86_variant in ['x64', 'x86']:
    RunGN(api, checkout_dir, '--android', '--android-cpu=' + x86_variant,
          '--no-lto')
    Build(api, checkout_dir, 'android_debug_' + x86_variant)


def BuildLinuxAndroidArm(api, checkout_dir):
  RunGN(api, checkout_dir, '--android', '--no-lto')
  Build(api, checkout_dir, 'android_debug')
  Build(api, checkout_dir, 'android_debug', ':dist')
  RunGN(api, checkout_dir, '--android', '--runtime-mode=release',
        '--android-cpu=arm')
  Build(api, checkout_dir, 'android_release', 'gen_snapshot')

  # Build and upload engines for the runtime modes that use AOT compilation.
  for runtime_mode in ['profile', 'release']:
    build_output_dir = 'android_' + runtime_mode

    RunGN(api, checkout_dir, '--android', '--runtime-mode=' + runtime_mode)
    Build(api, checkout_dir, build_output_dir)


def BuildLinux(api, checkout_dir):
  RunGN(api, checkout_dir, '--full-dart-sdk')
  Build(api, checkout_dir, 'host_debug')
  Build(api, checkout_dir, 'host_debug', 'create_full_sdk')
  RunGN(api, checkout_dir, '--unoptimized')
  Build(api, checkout_dir, 'host_debug_unopt')
  # analyze step needs dart ui sources
  Build(api, checkout_dir, 'host_debug_unopt', 'generate_dart_ui')
  RunGN(api, checkout_dir, '--runtime-mode=release')
  Build(api, checkout_dir, 'host_release')


def TestObservatory(api, checkout_dir):
  flutter_tester_path = checkout_dir.join('out/host_debug/flutter_tester')
  empty_main_path = checkout_dir.join(
      'flutter/shell/testing/observatory/empty_main.dart')
  test_path = checkout_dir.join('flutter/shell/testing/observatory/test.dart')
  test_cmd = ['dart', test_path, flutter_tester_path, empty_main_path]
  with api.context(cwd=checkout_dir):
    # Timeout after 5 minutes, this step is prone to hang
    api.step('test observatory and service protocol', test_cmd, timeout=5*60)


def GetCheckout(api):
  src_cfg = api.gclient.make_config()
  src_cfg.target_os = set(['android'])
  commits = {}
  # tryjobs don't have a gitiles_commit
  if api.buildbucket.gitiles_commit.id:
    commits = json.loads(api.gitiles.download_file(
        'https://dart.googlesource.com/linear_sdk_flutter_engine',
        COMMITS_JSON,
        api.buildbucket.gitiles_commit.id,
        step_test_data=lambda: api.gitiles.test_api.make_encoded_file(
            json.dumps({ENGINE_REPO: 'bar', SDK_REPO: 'foo'}))))
  engine_rev = commits.get(ENGINE_REPO, 'HEAD')
  flutter_rev = commits.get(FLUTTER_REPO, 'HEAD')
  sdk_rev = commits.get(SDK_REPO, 'HEAD')

  src_cfg.revisions = {
    'src/flutter': engine_rev,
    'src/third_party/dart': sdk_rev,
    'flutter': flutter_rev,
  }

  soln = src_cfg.solutions.add()
  soln.name = 'src/flutter'
  soln.url = \
      'https://dart.googlesource.com/%s' % ENGINE_REPO

  soln = src_cfg.solutions.add()
  soln.name = 'flutter'
  soln.url = \
      'https://dart.googlesource.com/%s' % FLUTTER_REPO

  api.gclient.c = src_cfg
  api.bot_update.ensure_checkout(ignore_input_commit=True,
                                 update_presentation=True)
  properties = api.step.active_result.presentation.properties
  properties['rev_engine'] = engine_rev
  properties['rev_flutter'] = flutter_rev
  properties['rev_sdk'] = sdk_rev
  properties['got_revision'] = api.buildbucket.gitiles_commit.id

  api.gclient.runhooks()

  with api.depot_tools.on_path(), api.context(env={'DEPOT_TOOLS_UPDATE': 0}):
    api.step('3xHEAD Flutter Hooks',
        ['src/third_party/dart/tools/3xhead_flutter_hooks.sh'])

  return flutter_rev


def CopyArtifacts(api, engine_src, cached_dest, file_paths):
  # cached_dest folder might not exist: flutter update-packages downloads only
  # artifacts that are needed by the connected devices and 3xHEAD bot
  # does not have any devices attached.
  api.file.ensure_directory('mkdir %s' % cached_dest, cached_dest)
  for path in file_paths:
    source, target = path, api.path.basename(path)

    api.file.remove('remove %s' % target, cached_dest.join(target))
    api.file.copy('copy %s' % target, engine_src.join(source),
                  cached_dest.join(target))


def UpdateCachedEngineArtifacts(api, flutter, engine_src):
  ICU_DATA_PATH = 'third_party/icu/flutter/icudtl.dat'
  CopyArtifacts(api, engine_src,
    flutter.join('bin', 'cache', 'artifacts', 'engine', 'linux-x64'),
    [ICU_DATA_PATH,
    'out/host_debug_unopt/flutter_tester',
    'out/host_debug_unopt/gen/flutter/lib/snapshot/isolate_snapshot.bin',
    'out/host_debug_unopt/gen/flutter/lib/snapshot/vm_isolate_snapshot.bin',
    'out/host_debug_unopt/gen/frontend_server.dart.snapshot',
    ]
  )

  CopyArtifacts(api, engine_src,
    flutter.join('bin', 'cache', 'artifacts', 'engine', 'android-arm-release',
                 'linux-x64'),
    ['out/android_release/clang_x64/gen_snapshot'])

  flutter_patched_sdk = flutter.join('bin', 'cache', 'artifacts', 'engine',
                                     'common', 'flutter_patched_sdk')
  flutter_patched_sdk_product = flutter.join('bin', 'cache', 'artifacts',
                                             'engine', 'common',
                                             'flutter_patched_sdk_product')
  dart_sdk = flutter.join('bin', 'cache', 'dart-sdk')
  # In case dart-sdk symlink was left from previous run we need to [remove] it,
  # rather than [rmtree] because rmtree is going to remove symlink target
  # folder. We are not able to use api.file classes for this because there is
  # no support for symlink checks or handling of error condition.
  api.step('cleanup dart-sdk', [
    '/bin/bash', '-c',
    'if [ -L "%(dir)s" ]; then rm "%(dir)s"; else rm -rf "%(dir)s"; fi' %
    {'dir': dart_sdk}])
  api.step('cleanup flutter_patched_sdk', [
    '/bin/bash', '-c',
    'if [ -L "%(dir)s" ]; then rm "%(dir)s"; else rm -rf "%(dir)s"; fi' %
    {'dir': flutter_patched_sdk}])
  api.step('cleanup flutter_patched_sdk_product', [
    '/bin/bash', '-c',
    'if [ -L "%(dir)s" ]; then rm "%(dir)s"; else rm -rf "%(dir)s"; fi' %
    {'dir': flutter_patched_sdk_product}])
  api.file.symlink('make cached dart-sdk point to just built dart sdk',
    engine_src.join('out', 'host_debug', 'dart-sdk'), dart_sdk)
  api.file.symlink(
    'make cached flutter_patched_sdk point to just built flutter_patched_sdk',
    engine_src.join('out', 'host_debug', 'flutter_patched_sdk'),
    flutter_patched_sdk)
  api.file.symlink(
    'make cached flutter_patched_sdk_product point to just built release '
    'version of flutter_patched_sdk',
    engine_src.join('out', 'host_release', 'flutter_patched_sdk'),
    flutter_patched_sdk_product)

  # In case there is a cached version of "flutter_tools.snapshot" we have to
  # delete it.
  flutter_tools_snapshot = flutter.join(
      'bin', 'cache', 'flutter_tools.snapshot')
  api.step('cleanup', [
    '/bin/bash', '-c', 'if [ -f "%(file)s" ]; then rm "%(file)s"; fi' %
    {'file': flutter_tools_snapshot}])


def TestFlutter(api, start_dir, just_built_dart_sdk):
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
  api.step('disable flutter analytics', [
      flutter_cmd, 'config', '--no-analytics'])
  with api.context(cwd=flutter):
    api.step('flutter update-packages',
             [flutter_cmd, 'update-packages'] + test_args)

    # Precache so that later flutter won't overwrite
    # updated artifacts.
    api.step('flutter precache', [flutter_cmd, 'precache'])

    # analyze.dart and test.dart have hardcoded references to
    # bin/cache/dart-sdk.  So we overwrite bin/cache/dart-sdk and
    # tightly-coupled frontend_server.dart.snapshot with links that point to
    # corresponding entries from binaries generated into [engine_src]
    UpdateCachedEngineArtifacts(api, flutter, engine_src)

    # runs all flutter tests similar to Cirrus as described on this page:
    # https://github.com/flutter/flutter/blob/master/CONTRIBUTING.md
    api.step('flutter analyze', [
        'dart', '--enable-asserts', 'dev/bots/analyze.dart', '--dart-sdk',
        just_built_dart_sdk], timeout=20*60) # 20 minutes
    shards = ['tests',
              # 'web_tests', - disabled due to flakiness
              #                https://github.com/flutter/flutter/pull/35792
              'tool_tests',
              'tool_coverage',
              'build_tests',
              'coverage',
              'integration_tests',
              'add2app_test']
    for shard in shards:
      with api.context(env={'SHARD': shard}):
        api.step('flutter test %s' % (shard),
                 test_cmd + test_args, timeout=120*60) # 2 hours


def RunSteps(api):
  start_dir = api.path['cache'].join('builder')

  with api.context(cwd=start_dir):
    # buildbot sets 'clobber' to the empty string which is falsey, check with
    # 'in'
    if 'clobber' in api.properties:
      api.file.rmcontents('everything', start_dir)
    flutter_rev = GetCheckout(api)

  api.goma.ensure_goma()

  checkout_dir = start_dir.join('src')
  KillTasks(api, checkout_dir)
  try:
    BuildAndTest(api, start_dir, checkout_dir, flutter_rev)
  finally:
    # TODO(aam): Go back to `ok_ret={0}` once dartbug.com/35549 is fixed
    KillTasks(api, checkout_dir, ok_ret='any')


def BuildAndTest(api, start_dir, checkout_dir, flutter_rev):
  run_env = {
    'GOMA_DIR':api.goma.goma_dir,
    # By setting 'ANALYZER_STATE_LOCATION_OVERRIDE' we force analyzer to emit
    # its cached state into the given folder. If something goes wrong with
    # the cache we can clobber it by requesting normal clobber via Buildbot
    # UI.
    'ANALYZER_STATE_LOCATION_OVERRIDE': start_dir.join('.dartServer')
  }
  with api.context(cwd=start_dir, env=run_env):
    BuildLinux(api, checkout_dir)
    prebuilt_dart_bin = checkout_dir.join('third_party', 'dart', 'tools',
      'sdks', 'dart-sdk', 'bin')
    engine_env = { 'PATH': api.path.pathsep.join((str(prebuilt_dart_bin),
      '%(PATH)s')) }
    just_built_dart_sdk = checkout_dir.join('out', 'host_debug', 'dart-sdk')
    flutter_env = {
      'PATH': api.path.pathsep.join((
          str(just_built_dart_sdk.join('bin')), '%(PATH)s')),
      # Prevent test.dart from using git merge-base to determine a fork point.
      # git merge-base doesn't work without a FETCH_HEAD, which isn't available
      # on the first run of a bot. The builder tests a single revision, so use
      # flutter_rev.
      'TEST_COMMIT_RANGE': flutter_rev,
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
        TestFlutter(api, start_dir, just_built_dart_sdk)


def GenTests(api):
  yield (api.test('flutter-engine-linux') + api.platform('linux', 64)
      + api.buildbucket.ci_build(
          builder='flutter-engine-linux',
          git_repo='https://dart.googlesource.com/linear_sdk_flutter_engine',
          revision='f' * 8)
      + api.properties(bot_id='fake-m1', clobber='')
      + api.runtime(is_luci=True, is_experimental=False))

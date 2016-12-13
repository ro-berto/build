# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'file',
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
  RunGN(api, '--unoptimized')
  Build(api, 'host_debug_unopt', 'generate_dart_ui')

  checkout = api.path['start_dir'].join('src')
  api.step('analyze dart_ui', ['/bin/sh', 'flutter/travis/analyze.sh'],
           cwd=checkout)

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
  RunGN(api, '--unoptimized')
  Build(api, 'host_debug_unopt')

def TestObservatory(api):
  checkout = api.path['start_dir'].join('src')
  sky_shell_path = checkout.join('out/host_debug_unopt/sky_shell')
  empty_main_path = checkout.join(
      'flutter/shell/testing/observatory/empty_main.dart')
  test_path = checkout.join('flutter/shell/testing/observatory/test.dart')
  test_cmd = ['dart', test_path, sky_shell_path, empty_main_path]
  api.step('test observatory and service protocol', test_cmd, cwd=checkout)

def GetCheckout(api):
  src_cfg = api.gclient.make_config()
  src_cfg.target_os = set(['android'])
  src_cfg.revisions = {
    'src/flutter': api.properties.get('rev_engine') or
                   api.properties.get('revision') or 'HEAD',
    'src/dart': api.properties.get('rev_sdk') or 'HEAD',
  }

  soln = src_cfg.solutions.add()
  soln.name = 'src/flutter'
  soln.url = \
      'https://chromium.googlesource.com/external/github.com/flutter/engine'

  api.gclient.c = src_cfg
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()

def RunSteps(api):
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmcontents('everything', api.path['start_dir'])
  GetCheckout(api)

  checkout = api.path['start_dir'].join('src')
  dart_bin = checkout.join('third_party', 'dart-sdk', 'dart-sdk', 'bin')
  env = { 'PATH': api.path.pathsep.join((str(dart_bin), '%(PATH)s')) }

  # The context adds dart to the path, only needed for the analyze step for now.
  with api.step.context({'env': env}):
    AnalyzeDartUI(api)

    BuildLinux(api)
    TestObservatory(api)
    BuildLinuxAndroidArm(api)
    BuildLinuxAndroidx86(api)

def GenTests(api):
  yield (api.test('flutter-engine-linux') + api.platform('linux', 64)
      + api.properties(mastername='client.dart.internal',
            buildername='flutter-engine-linux',
            slavename='fake-m1', clobber='',
            rev_sdk='foo', rev_engine='bar'))

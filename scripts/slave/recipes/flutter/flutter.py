# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib

DEPS = [
  'build',
  'depot_tools/git',
  'file',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
  'recipe_engine/python',
  'recipe_engine/url',
  'zip',
]

BUCKET_NAME = 'flutter_infra'


def GetCloudPath(api, git_hash, path):
  return 'flutter/%s/%s' % (git_hash, path)


# def TestCreateAndLaunch(api):
#   with MakeTempDir(api) as temp_dir:
#     api.step('shutdown simulator', ['killall', 'Simulator'], cwd=temp_dir)
#     api.step('erase simulator', ['/usr/bin/xcrun', 'simctl', 'erase', 'all'],
#         cwd=temp_dir)
#     api.step('test create', ['flutter', 'create', '--with-driver-test',
#         'sample_app'], cwd=temp_dir)
#     app_path = temp_dir.join('sample_app')
#     api.step('drive sample_app', ['flutter', 'drive', '--verbose'],
#         cwd=app_path)
#     api.step('dump logs', ['tail', '-n', '--verbose'],
#         cwd=app_path)

# TODO(eseidel): Would be nice to have this on api.path or api.file.
# @contextlib.contextmanager
# def MakeTempDir(api):
#   try:
#     temp_dir = api.path.mkdtemp('tmp')
#     yield temp_dir
#   finally:
#     api.file.rmtree('temp dir', temp_dir)


def BuildExamples(api, git_hash, flutter_executable):
  def BuildAndArchive(api, app_dir, apk_name):
    app_path = api.path['checkout'].join(app_dir)
    with api.context(cwd=app_path):
      api.step('flutter build apk %s' % api.path.basename(app_dir),
          [flutter_executable, '-v', 'build', 'apk'])

      # TODO(cbracken): re-enable once cocoapods is installed on the Mac bots.
      #if api.platform.is_mac:
      #  app_name = api.path.basename(app_dir)
      #  # Disable codesigning since this bot has no developer cert.
      #  api.step(
      #    'flutter build ios %s' % app_name,
      #    [flutter_executable, '-v', 'build', 'ios', '--no-codesign'],
      #  )
      #  api.step(
      #    'flutter build ios debug %s' % app_name,
      #    [flutter_executable, '-v', 'build', 'ios', '--no-codesign', '--debug'],
      #  )
      #  api.step(
      #    'flutter build ios simulator %s' % app_name,
      #    [flutter_executable, '-v', 'build', 'ios', '--simulator'],
      #  )

    # This is linux just to have only one bot archive at once.
    if api.platform.is_linux:
      cloud_path = GetCloudPath(api, git_hash, 'examples/%s' % apk_name)
      apk_path = app_path.join('build', 'app', 'outputs', 'apk', 'app.apk')
      api.gsutil.upload(apk_path, BUCKET_NAME, cloud_path,
          link_name=apk_name, name='upload %s' % apk_name)

  # TODO(eseidel): We should not have to hard-code the desired apk name here.
  BuildAndArchive(api, 'examples/stocks', 'Stocks.apk')
  BuildAndArchive(api, 'examples/flutter_gallery', 'Gallery.apk')


def RunFindXcode(api, ios_tools_path, target_version):
  """Locates and switches to a version of Xcode matching target_version."""
  args = [
      '--json-file', api.json.output(),
      '--version', target_version,
  ]
  result = api.build.python(
      'set_xcode_version',
      ios_tools_path.join('build', 'bots', 'scripts', 'find_xcode.py'),
      args)
  return result.json.output


def SetupXcode(api):
  # Clone the chromium iOS tools to ios/ subdir.
  # NOTE: nothing special about the ref other than to pin for stability.
  ios_tools_path = api.path['start_dir'].join('ios')
  api.git.checkout(
      'https://chromium.googlesource.com/chromium/src/ios',
      ref='69b7c1b160e7107a6a98d948363772dc9caea46f',
      dir_path=ios_tools_path, recursive=True, step_suffix='_ios_tools')

  target_version = '7.0'
  xcode_json = RunFindXcode(api, ios_tools_path, target_version)
  if not xcode_json['matches']:
    raise api.step.StepFailure('Xcode %s not found' % target_version)


def InstallGradle(api, checkout):
  api.url.get_file(
      'https://services.gradle.org/distributions/gradle-2.14.1-bin.zip',
      checkout.join('dev', 'bots', 'gradle-2.14.1-bin.zip'),
      step_name='download gradle')
  api.zip.unzip(
      'unzip gradle',
      checkout.join('dev', 'bots', 'gradle-2.14.1-bin.zip'),
      checkout.join('dev', 'bots', 'gradle'))
  update_android_cmd = ['cmd.exe', '/C'] if api.platform.is_win else ['sh', '-c']
  update_android_cmd.append(
      'echo y | %s update sdk --no-ui --all --filter build-tools-25.0.3,android-25,extra-android-m2repository' %
      checkout.join('dev', 'bots', 'android_tools', 'sdk', 'tools', 'android'))
  api.step('update android tools', update_android_cmd)


def RunSteps(api):
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmcontents('everything', api.path['start_dir'])

  git_hash = api.git.checkout(
      'https://chromium.googlesource.com/external/github.com/flutter/flutter',
      ref=api.properties.get('revision'),
      recursive=True, set_got_revision=True)
  checkout = api.path['checkout']

  api.python('download android tools',
      checkout.join('dev', 'bots', 'download_android_tools.py'), ['-t', 'sdk'])

  InstallGradle(api, checkout)

  dart_bin = checkout.join('bin', 'cache', 'dart-sdk', 'bin')
  flutter_bin = checkout.join('bin')
  gradle_bin = checkout.join('dev', 'bots', 'gradle', 'gradle-2.14.1', 'bin')
  # TODO(eseidel): This is named exactly '.pub-cache' as a hack around
  # a regexp in flutter_tools analyze.dart which is in turn a hack around:
  # https://github.com/dart-lang/sdk/issues/25722
  pub_cache = api.path['start_dir'].join('.pub-cache')
  env = {
    'PATH': api.path.pathsep.join((str(flutter_bin), str(dart_bin), str(gradle_bin),
        '%(PATH)s')),
    # Setup our own pub_cache to not affect other slaves on this machine.
    'PUB_CACHE': pub_cache,
    'ANDROID_HOME': checkout.join('dev', 'bots', 'android_tools'),
  }

  # The context adds dart-sdk tools to PATH sets PUB_CACHE.
  with api.context(env=env):
    if api.platform.is_mac:
      SetupXcode(api)

    flutter_executable = 'flutter' if not api.platform.is_win else 'flutter.bat'
    dart_executable = 'dart' if not api.platform.is_win else 'dart.exe'

    with api.context(cwd=checkout):
      api.step('download dependencies', [flutter_executable, 'update-packages'])
      api.step('flutter doctor', [flutter_executable, 'doctor'])
      api.step('test.dart', [dart_executable, 'dev/bots/test.dart'])

    BuildExamples(api, git_hash, flutter_executable)

    # TODO(yjbanov): we do not yet have Android devices hooked up, nor do we
    # support the Android emulator. For now, only run on iOS Simulator.
    #
    # if api.platform.is_mac:
    #   TestCreateAndLaunch(api)


def GenTests(api):
  for platform in ('mac', 'linux', 'win'):
    test = (api.test(platform) + api.platform(platform, 64) +
        api.properties(clobber=''))
    if platform == 'mac':
      test += (
        api.step_data('set_xcode_version', api.json.output({
          'matches': {
            '/Applications/Xcode7.0.app': '7.0 (7A220)'
          }
        }))
      )
    yield test

  yield (
    api.test('mac_cannot_find_xcode') +
    api.platform('mac', 64) +
    api.properties(revision='1234abcd') +
    api.properties(clobber='') +
    api.step_data('set_xcode_version', api.json.output({
      'matches': {}
    }))
  )

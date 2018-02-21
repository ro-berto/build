# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import re

DEPS = [
    'build',
    'depot_tools/git',
    'depot_tools/gsutil',
    'recipe_engine/context',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'recipe_engine/python',
    'recipe_engine/url',
    'zip',
]

BUCKET_NAME = 'flutter_infra'
PACKAGED_BRANCH_RE = re.compile(r'(dev|beta|release)$')


def GetPuppetApiTokenPath(api, token_name):
  """Returns the path to a the token file

  The file is located where ChromeOps Puppet drops generic secrets."""
  return api.path.join(
      api.path.abspath(api.path.sep), 'creds', 'generic',
      'generic-%s' % token_name)


def GetCloudPath(api, git_hash, path):
  return 'flutter/%s/%s' % (git_hash, path)


def BuildExamples(api, git_hash, flutter_executable):

  def BuildAndArchive(api, app_dir, apk_name):
    app_path = api.path['checkout'].join(app_dir)
    with api.context(cwd=app_path):
      api.step('flutter build apk %s' % api.path.basename(app_dir),
               [flutter_executable, '-v', 'build', 'apk'])

      if api.platform.is_mac:
        app_name = api.path.basename(app_dir)
        # Disable codesigning since this bot has no developer cert.
        api.step(
            'flutter build ios %s' % app_name,
            [flutter_executable, '-v', 'build', 'ios', '--no-codesign'],
        )
        api.step(
            'flutter build ios debug %s' % app_name,
            [
                flutter_executable, '-v', 'build', 'ios', '--no-codesign',
                '--debug'
            ],
        )
        api.step(
            'flutter build ios simulator %s' % app_name,
            [flutter_executable, '-v', 'build', 'ios', '--simulator'],
        )

    # This is linux just to have only one bot archive at once.
    if api.platform.is_linux:
      cloud_path = GetCloudPath(api, git_hash, 'examples/%s' % apk_name)
      apk_path = app_path.join('build', 'app', 'outputs', 'apk', 'app.apk')
      api.gsutil.upload(
          apk_path,
          BUCKET_NAME,
          cloud_path,
          link_name=apk_name,
          name='upload %s' % apk_name)

  # TODO(eseidel): We should not have to hard-code the desired apk name here.
  BuildAndArchive(api, 'examples/stocks', 'Stocks.apk')
  BuildAndArchive(api, 'examples/flutter_gallery', 'Gallery.apk')


def RunFindXcode(api, ios_tools_path, target_version):
  """Locates and switches to a version of Xcode matching target_version."""
  args = [
      '--json-file',
      api.json.output(),
      '--version',
      target_version,
  ]
  result = api.build.python('set_xcode_version',
                            ios_tools_path.join('build', 'bots', 'scripts',
                                                'find_xcode.py'), args)
  return result.json.output


def SetupXcode(api):
  # Clone the chromium iOS tools to ios/ subdir.
  # NOTE: nothing special about the ref other than to pin for stability.
  ios_tools_path = api.path['start_dir'].join('ios')
  api.git.checkout(
      'https://chromium.googlesource.com/chromium/src/ios',
      ref='69b7c1b160e7107a6a98d948363772dc9caea46f',
      dir_path=ios_tools_path,
      recursive=True,
      step_suffix='ios_tools')

  target_version = '9.0.1'
  xcode_json = RunFindXcode(api, ios_tools_path, target_version)
  if not xcode_json['matches']:
    raise api.step.StepFailure('Xcode %s not found' % target_version)


def InstallGradle(api, checkout):
  api.url.get_file(
      'https://services.gradle.org/distributions/gradle-2.14.1-bin.zip',
      checkout.join('dev', 'bots', 'gradle-2.14.1-bin.zip'),
      step_name='download gradle')
  api.zip.unzip('unzip gradle',
                checkout.join('dev', 'bots', 'gradle-2.14.1-bin.zip'),
                checkout.join('dev', 'bots', 'gradle'))
  sdkmanager_executable = 'sdkmanager.bat' if api.platform.is_win else 'sdkmanager'
  sdkmanager_list_cmd = ['cmd.exe',
                         '/C'] if api.platform.is_win else ['sh', '-c']
  sdkmanager_list_cmd.append(
      '%s --list' % checkout.join('dev', 'bots', 'android_tools', 'sdk',
                                  'tools', 'bin', sdkmanager_executable))
  api.step('print installed android SDK components', sdkmanager_list_cmd)


def UploadFlutterCoverage(api):
  """Uploads the Flutter coverage output to cloud storage and Coveralls.
  """
  # Upload latest coverage to cloud storage.
  checkout = api.path['checkout']
  coverage_path = checkout.join('packages', 'flutter', 'coverage', 'lcov.info')
  api.gsutil.upload(
      coverage_path,
      BUCKET_NAME,
      GetCloudPath(api, 'coverage', 'lcov.info'),
      link_name='lcov.info',
      name='upload coverage data')

  # Upload latest coverage to Coveralls.
  token_path = GetPuppetApiTokenPath(api, 'flutter-coveralls-api-token')
  with api.context(cwd=checkout.join('packages', 'flutter')):
    api.build.python(
        'upload coverage data to Coveralls',
        api.resource('upload_to_coveralls.py'),
        ['--token-file=%s' % token_path,
         '--coverage-path=%s' % coverage_path])


def CreateAndUploadFlutterPackage(api, git_hash):
  """Prepares, builds, and uploads an all-inclusive archive package."""
  dart_executable = 'dart' if not api.platform.is_win else 'dart.exe'
  work_dir = api.path['start_dir'].join('archive')
  prepare_script = api.path['checkout'].join('dev', 'bots',
                                             'prepare_package.dart')
  api.file.rmtree('clean archive work directory', work_dir)
  api.file.ensure_directory('(re)create archive work directory', work_dir)
  with api.context(cwd=api.path['start_dir']):
    api.step('prepare, create and publish a flutter archive', [
        dart_executable, '--assert-initializer', prepare_script,
        '--temp_dir=%s' % work_dir,
        '--revision=%s' % git_hash,
        '--branch=%s' % api.properties['branch'],
        '--publish'
    ])


def RunSteps(api):
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmcontents('everything', api.path['start_dir'])

  git_hash = api.git.checkout(
      'https://chromium.googlesource.com/external/github.com/flutter/flutter',
      ref=api.properties.get('revision'),
      recursive=True,
      set_got_revision=True)
  checkout = api.path['checkout']

  dart_bin = checkout.join('bin', 'cache', 'dart-sdk', 'bin')
  flutter_bin = checkout.join('bin')
  gradle_bin = checkout.join('dev', 'bots', 'gradle', 'gradle-2.14.1', 'bin')
  path_prefix = api.path.pathsep.join((str(flutter_bin), str(dart_bin),
                                       str(gradle_bin)))

  if api.platform.is_win:
    path_prefix = api.path.pathsep.join((path_prefix,
                                         api.path.join('%(PROGRAMFILES)s',
                                                       '7-Zip-A', 'x64')))

  # TODO(eseidel): This is named exactly '.pub-cache' as a hack around
  # a regexp in flutter_tools analyze.dart which is in turn a hack around:
  # https://github.com/dart-lang/sdk/issues/25722
  pub_cache = checkout.join('.pub-cache')
  env = {
      'PATH': api.path.pathsep.join((path_prefix, '%(PATH)s')),
      # Setup our own pub_cache to not affect other slaves on this machine,
      # and so that the pre-populated pub cache is contained in the package.
      'PUB_CACHE': pub_cache,
      'ANDROID_HOME': checkout.join('dev', 'bots', 'android_tools'),
  }

  flutter_executable = 'flutter' if not api.platform.is_win else 'flutter.bat'
  dart_executable = 'dart' if not api.platform.is_win else 'dart.exe'

  # The context adds dart-sdk tools to PATH and sets PUB_CACHE.
  with api.context(env=env, cwd=checkout):
    api.step('flutter doctor', [flutter_executable, 'doctor'])
    api.step('download dependencies', [flutter_executable, 'update-packages'])
    branch = api.properties.get('branch')
    if (branch and PACKAGED_BRANCH_RE.match(branch)):
      CreateAndUploadFlutterPackage(api, git_hash)
    else:
      api.step("Skipping packaging on %s branch." % branch, cmd=None)

  if api.platform.is_mac:
    SetupXcode(api)
  api.python('download android tools',
             checkout.join('dev', 'bots', 'download_android_tools.py'),
             ['-t', 'sdk'])
  InstallGradle(api, checkout)

  with api.context(env=env, cwd=checkout):
    shards = ['tests'] if not api.platform.is_linux else ['tests', 'coverage']
    for shard in shards:
      shard_env = env
      shard_env['SHARD'] = shard
      with api.context(env=shard_env):
        api.step('run test.dart for %s shard' % shard,
                 [dart_executable,
                  checkout.join('dev', 'bots', 'test.dart')])
      if shard == 'coverage':
        UploadFlutterCoverage(api)

    BuildExamples(api, git_hash, flutter_executable)


def GenTests(api):
  for platform in ('mac', 'linux', 'win'):
    for branch in ('master', 'dev', 'beta', 'release'):
      test = (
          api.test('%s_%s' % (platform, branch)) + api.platform(platform, 64) +
          api.properties(clobber='', branch=branch))
      if platform == 'mac':
        test += (
            api.step_data('set_xcode_version',
                          api.json.output({
                              'matches': {
                                  '/Applications/Xcode9.0.app': '9.0.1 (9A1004)'
                              }
                          })))
      if platform == 'linux':
        test += (
            api.override_step_data('upload coverage data to Coveralls',
                                   api.raw_io.output('')))
      yield test

  yield (api.test('mac_cannot_find_xcode') + api.platform('mac', 64) +
         api.properties(revision='1234abcd') + api.properties(clobber='') +
         api.step_data('set_xcode_version', api.json.output({
             'matches': {}
         })))

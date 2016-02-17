# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib

DEPS = [
  'depot_tools/git',
  'file',
  'gsutil',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]

BUCKET_NAME = 'flutter_infra'


def GetCloudPath(api, git_hash, path):
  return 'flutter/%s/%s' % (git_hash, path)


def UpdatePackages(api):
  update_packages = api.path['checkout'].join('dev', 'update_packages.dart')
  api.step('update packages', ['dart', update_packages])


def PopulateFlutterCache(api):
  flutter_package = api.path['checkout'].join('packages', 'flutter')
  populate_cmd = ['flutter', 'cache', 'populate']
  api.step('populate flutter cache', populate_cmd, cwd=flutter_package)


def AnalyzeFlutter(api):
  analyze_cmd = [
    'flutter',
    'analyze',
    '--flutter-repo',
    '--no-current-directory',
    '--no-current-package',
    '--congratulate'
  ]
  api.step('flutter analyze', analyze_cmd, cwd=api.path['checkout'])


def TestFlutterPackagesAndExamples(api):
  checkout = api.path['checkout']

  def _pub_test(path):
    api.step('test %s' % path, ['pub', 'run', 'test', '-j1'],
      cwd=checkout.join(path))

  def _flutter_test(path):
    # TODO(eseidel): Sadly tests are linux-only for now. :(
    # https://github.com/flutter/flutter/issues/1707
    if api.platform.is_linux:
      api.step('test %s' % path, ['flutter', 'test'], cwd=checkout.join(path))

  _pub_test('packages/cassowary')
  _flutter_test('packages/flutter')
  _pub_test('packages/flutter_tools')
  _pub_test('packages/flx')
  _pub_test('packages/newton')

  _flutter_test('examples/stocks')


# TODO(eseidel): Would be nice to have this on api.path or api.file.
@contextlib.contextmanager
def MakeTempDir(api):
  try:
    temp_dir = api.path.mkdtemp('tmp')
    yield temp_dir
  finally:
    api.file.rmtree('temp dir', temp_dir)


def GenerateDocs(api, pub_cache):
  # TODO(abarth): Do we still need a specific dartdoc version?
  activate_cmd = ['pub', 'global', 'activate', 'dartdoc', '0.8.4']
  api.step('pub global activate dartdoc', activate_cmd)
  dartdoc = pub_cache.join('bin', 'dartdoc')

  checkout = api.path['checkout']
  flutter_styles = checkout.join('packages', 'flutter', 'doc', 'styles.html')
  analytics = checkout.join('doc', '_analytics.html')
  header_contents = '\n'.join([
    api.file.read('Read styles.html', flutter_styles, test_data='styles'),
    api.file.read('Read _analytics.html', analytics, test_data='analytics'),
  ])

  with MakeTempDir(api) as temp_dir:
    header = temp_dir.join('_header.html')
    api.file.write('Write _header.html', header, header_contents)

    # NOTE: If you add to this list, be sure to edit doc/index.html
    DOCUMENTED_PACKAGES = [
      'packages/flutter',
      'packages/playfair',
      'packages/cassowary',
      'packages/flutter_test',
      'packages/flutter_sprites',
    ]
    for package in DOCUMENTED_PACKAGES:
        package_path = checkout.join(package)
        api.step('dartdoc %s' % package, [dartdoc, '--header', header],
            cwd=package_path)
        api_path = package_path.join('doc', 'api')
        remote_path = 'gs://docs.flutter.io/%s' % package_path.pieces[-1]
        # Use rsync instead of copy to delete any obsolete docs.
        api.gsutil(['-m', 'rsync', '-d', '-r', api_path, remote_path],
            name='rsync %s/doc/api' % package)

    index_path = checkout.join('doc', 'index.html')
    api.gsutil.upload(index_path, 'docs.flutter.io', 'index.html',
        name='upload doc/index.html')


def BuildExamples(api, git_hash):
  def ArchiveAPK(api, app_dir, apk_name):
    app_path = api.path['checkout'].join(app_dir)
    api.step('flutter apk %s' % app_dir, ['flutter', 'apk'], cwd=app_path)
    # This is linux just to have only one bot archive at once.
    if api.platform.is_linux:
      cloud_path = GetCloudPath(api, git_hash, 'examples/%s' % apk_name)
      api.gsutil.upload(app_path.join('build/app.apk'), BUCKET_NAME, cloud_path,
          link_name=apk_name, name='upload %s' % apk_name)

  # TODO(eseidel): We should not have to hard-code the desired apk name here.
  ArchiveAPK(api, 'examples/stocks', 'Stocks.apk')
  ArchiveAPK(api, 'examples/material_gallery', 'Gallery.apk')


def RunSteps(api):
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmcontents('everything', api.path['slave_build'])

  git_hash = api.git.checkout(
      'https://chromium.googlesource.com/external/github.com/flutter/flutter',
      recursive=True, set_got_revision=True)
  checkout = api.path['checkout']

  download_sdk = checkout.join('infra', 'download_dart_sdk.py')
  api.step('download dart sdk', [download_sdk])

  api.step('download android tools',
      [checkout.join('infra', 'download_android_tools.py')])


  dart_bin = checkout.join('infra', 'dart-sdk', 'dart-sdk', 'bin')
  flutter_bin = checkout.join('bin')
  # TODO(eseidel): This is named exactly '.pub-cache' as a hack around
  # a regexp in flutter_tools analyze.dart which is in turn a hack around:
  # https://github.com/dart-lang/sdk/issues/25722
  pub_cache = api.path['slave_build'].join('.pub-cache')
  env = {
    'PATH': api.path.pathsep.join((str(flutter_bin), str(dart_bin),
        '%(PATH)s')),
    # Setup our own pub_cache to not affect other slaves on this machine.
    'PUB_CACHE': pub_cache,
    'ANDROID_HOME': checkout.join('infra', 'android_tools'),
  }

  # The context adds dart-sdk tools to PATH sets PUB_CACHE.
  with api.step.context({'env': env}):
    UpdatePackages(api)
    PopulateFlutterCache(api)
    api.step('flutter doctor', ['flutter', 'doctor'])
    AnalyzeFlutter(api)
    TestFlutterPackagesAndExamples(api)
    BuildExamples(api, git_hash)

    # TODO(eseidel): We only want to generate one copy of the docs at a time
    # otherwise multiple rsyncs could race, causing badness. We'll eventually
    # need both a lock on the bucket, as well as some assurance that we're
    # always moving the docs forward. Possibly by using a separate builder.
    # Until then, only generate on linux to reduce the chance of race.
    if api.platform.is_linux:
      # TODO(eseidel): Is there a way for GenerateDocs to read PUB_CACHE from
      # the env instead of me passing it in?
      GenerateDocs(api, pub_cache)


def GenTests(api):
  for platform in ('mac', 'linux'):
    yield (api.test(platform) + api.platform(platform, 64) +
        api.properties(clobber=''))

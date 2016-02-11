# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'file',
  'gsutil',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
  'zip',
]

BUCKET_NAME = 'flutter_infra'

def GetCloudPath(api, path):
  # TODO(eseidel): api.bot_update.properties is supposedly a known api wart.
  # iannucci says it will be improved at some point.
  git_hash = api.bot_update.properties['got_engine_revision']
  return 'flutter/%s/%s' % (git_hash, path)


def Build(api, config, *targets):
  checkout = api.path['checkout']
  build_dir = checkout.join('out/%s' % config)
  ninja_args = ['ninja', '-C', build_dir]
  ninja_args.extend(targets)
  api.step('build %s' % config, ninja_args)


def RunGN(api, *args):
  checkout = api.path['checkout']
  gn_cmd = [checkout.join('sky/tools/gn')]
  gn_cmd.extend(args)
  api.step('gn %s' % ' '.join(args), gn_cmd)


# TODO(eseidel): This belongs as api.zip.ZipPackage.add_files
def AddFiles(pkg, relative_paths):
  for path in relative_paths:
    pkg.add_file(pkg.root.join(path))


def UploadArtifacts(api, platform, file_paths):
  with MakeTempDir(api) as temp_dir:
    local_zip = temp_dir.join('artifacts.zip')
    remote_name = '%s/artifacts.zip' % platform
    remote_zip = GetCloudPath(api, remote_name)
    pkg = api.zip.make_package(api.path['checkout'], local_zip)
    AddFiles(pkg, file_paths)

    pkg.zip('Zip %s Artifacts' % platform)
    api.gsutil.upload(local_zip, BUCKET_NAME, remote_zip,
        name='upload %s' % remote_name)


# TODO(eseidel): Would be nice to have this on api.path or api.file.
@contextlib.contextmanager
def MakeTempDir(api):
  try:
    temp_dir = api.path.mkdtemp('tmp')
    yield temp_dir
  finally:
    api.file.rmtree('temp dir', temp_dir)


def AnalyzeDartUI(api):
  RunGN(api, '--debug')
  Build(api, 'Debug', 'generate_dart_ui')

  checkout = api.path['checkout']
  api.step('analyze dart_ui', ['/bin/sh', 'travis/analyze.sh'], cwd=checkout)


def BuildLinuxAndroid(api):
  RunGN(api, '--release', '--android', '--enable-firebase', '--enable-gcm')
  Build(api, 'android_Release', 'apks/SkyShell.apk', 'flutter.mojo',
      'sky/services/gcm', 'sky/services/firebase')
  UploadArtifacts(api, 'android-arm', [
    'build/android/ant/chromium-debug.keystore',
    'out/android_Release/apks/SkyShell.apk',
    'out/android_Release/flutter.mojo',
    # Unclear if this is the right way to work around draconian 80c rule:
    'out/android_Release/gen/sky/shell/shell/shell/libs/armeabi-v7a/' +
    'libsky_shell.so',
    'out/android_Release/icudtl.dat',

    # TODO(mpcomplete): stop bundling classes.dex once
    # https://github.com/flutter/flutter/pull/1263 lands.
    'out/android_Release/gen/sky/shell/shell/classes.dex.jar',
    'out/android_Release/gen/sky/shell/shell/classes.dex',
  ])

  def UploadService(name):
    def Upload(from_path, to_path):
      api.gsutil.upload(from_path, BUCKET_NAME, GetCloudPath(api, to_path),
          name='upload %s' % to_path)

    def ServicesOut(path):
      checkout = api.path['checkout']
      return checkout.join('out/android_Release/gen/sky/services/%s' % path)

    dex_jar = '%s/%s_lib.dex.jar' % (name, name)
    interfaces_jar = '%s/interfaces_java.dex.jar' % (name)
    Upload(ServicesOut(dex_jar), dex_jar)
    Upload(ServicesOut(interfaces_jar), interfaces_jar)

  UploadService('gcm')
  UploadService('firebase')


def BuildLinux(api):
  RunGN(api, '--release')
  Build(api, 'Release')
  UploadArtifacts(api, 'linux-x64', [
    'out/Release/flutter.mojo',
    'out/Release/icudtl.dat',
    'out/Release/sky_shell',
    'out/Release/sky_snapshot',
  ])


def TestObservatory(api):
  checkout = api.path['checkout']
  sky_shell_path = checkout.join('out/Release/sky_shell')
  empty_main_path = \
      checkout.join('sky/shell/testing/observatory/empty_main.dart')
  test_path = checkout.join('sky/shell/testing/observatory/test.dart')
  test_cmd = ['dart', test_path, sky_shell_path, empty_main_path]
  api.step('test observatory and service protocol', test_cmd, cwd=checkout)


def BuildMac(api):
  RunGN(api, '--release')
  Build(api, 'Release', 'sky_snapshot')
  UploadArtifacts(api, 'darwin-x64', [
    'out/Release/sky_snapshot'
  ])


def GenerateXcodeProject(api):
  checkout = api.path['checkout']
  out_dir = checkout.join('out')

  RunGN(api, '--release', '--ios', '--simulator')
  Build(api, 'ios_sim_Release')

  RunGN(api, '--release', '--ios')
  Build(api, 'ios_Release')

  # Copy device 'Flutter' directory to a deploy dir:
  deploy_dir = out_dir.join('FlutterXcode')
  api.file.rmtree('deployment directory', deploy_dir)
  device_flutter = out_dir.join('ios_Release/Flutter')
  api.file.copytree('copy sim', device_flutter, deploy_dir)

  # Copy the missing simulator tools into the deploy dir:
  sim_flutter = out_dir.join('ios_sim_Release/Flutter')
  sim_tools = 'Tools/iphonesimulator'
  api.file.copytree('copy simulator tools', sim_flutter.join(sim_tools),
      deploy_dir.join(sim_tools))

  # Zip the whole thing and upload it to cloud storage:
  flutter_zip = out_dir.join('FlutterXcode.zip')
  api.zip.directory('make FlutterXcode.zip', deploy_dir, flutter_zip)

  remote_name = 'ios/FlutterXcode.zip'
  cloud_path =  GetCloudPath(api, remote_name)
  api.gsutil.upload(flutter_zip, BUCKET_NAME, cloud_path,
      name='upload %s' % remote_name)


def GetCheckout(api):
  src_cfg = api.gclient.make_config(GIT_MODE=True)
  soln = src_cfg.solutions.add()
  soln.name = 'src'
  soln.url = \
      'https://chromium.googlesource.com/external/github.com/flutter/engine'
  # TODO(eseidel): What does parent_got_revision_mapping do?  Do I care?
  src_cfg.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'
  src_cfg.target_os = set(['android'])
  api.gclient.c = src_cfg
  api.gclient.c.got_revision_mapping['src'] = 'got_engine_revision'
  # TODO(eseidel): According to iannucci force=True is required.
  # See https://codereview.chromium.org/1690713003#msg6
  api.bot_update.ensure_checkout(force=True)
  api.gclient.runhooks()


def RunSteps(api):
  GetCheckout(api)

  checkout = api.path['checkout']
  dart_bin = checkout.join('third_party', 'dart-sdk', 'dart-sdk', 'bin')
  env = { 'PATH': api.path.pathsep.join((str(dart_bin), '%(PATH)s')) }

  # The context adds dart to the path, only needed for the analyze step for now.
  with api.step.context({'env': env}):
    AnalyzeDartUI(api)

    if api.platform.is_linux:
      api.step('download android tools',
        [checkout.join('tools/android/download_android_tools.py')])
      BuildLinux(api)
      TestObservatory(api)
      BuildLinuxAndroid(api)

    if api.platform.is_mac:
      BuildMac(api)
      GenerateXcodeProject(api)


def GenTests(api):
  # A valid commit to flutter/engine, to make the gsutil urls look real.
  for platform in ('mac', 'linux'):
    yield (api.test(platform) + api.platform(platform, 64)
        + api.properties(mastername='client.flutter',
              buildername='%s Engine' % platform.capitalize(),
              slavename='fake-m1'))

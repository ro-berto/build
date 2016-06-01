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
  # TODO(eseidel): api.bot_update.last_returned_properties is supposedly a known
  # api wart. iannucci says it will be improved at some point.
  git_hash = api.bot_update.last_returned_properties['got_engine_revision']
  return 'flutter/%s/%s' % (git_hash, path)


def Build(api, config, *targets):
  checkout = api.path['checkout']
  build_dir = checkout.join('out/%s' % config)
  ninja_args = ['ninja', '-C', build_dir]
  ninja_args.extend(targets)
  api.step('build %s' % ' '.join([config] + list(targets)), ninja_args)


def RunGN(api, *args):
  checkout = api.path['checkout']
  gn_cmd = [checkout.join('sky/tools/gn')]
  gn_cmd.extend(args)
  api.step('gn %s' % ' '.join(args), gn_cmd)


def AddFiles(api, pkg, relative_paths):
  for path in relative_paths:
    pkg.add_file(pkg.root.join(path), archive_name=api.path.basename(path))


def UploadArtifacts(api, platform, file_paths, archive_name='artifacts.zip'):
  with MakeTempDir(api) as temp_dir:
    local_zip = temp_dir.join('artifacts.zip')
    remote_name = '%s/%s' % (platform, archive_name)
    remote_zip = GetCloudPath(api, remote_name)
    pkg = api.zip.make_package(api.path['checkout'], local_zip)
    AddFiles(api, pkg, file_paths)

    pkg.zip('Zip %s Artifacts' % platform)
    api.gsutil.upload(local_zip, BUCKET_NAME, remote_zip,
        name='upload "%s"' % remote_name)


def UploadDartPackage(api, package_name):
  with MakeTempDir(api) as temp_dir:
    local_zip = temp_dir.join('%s.zip' % package_name)
    remote_name = '%s.zip' % package_name
    remote_zip = GetCloudPath(api, remote_name)
    parent_dir = api.path['checkout'].join(
        'out/android_debug/dist/packages')
    pkg = api.zip.make_package(parent_dir, local_zip)
    pkg.add_directory(parent_dir.join(package_name))
    pkg.zip('Zip %s Package' % package_name)
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
  RunGN(api, '--unoptimized')
  Build(api, 'host_debug_unopt', 'generate_dart_ui')

  checkout = api.path['checkout']
  api.step('analyze dart_ui', ['/bin/sh', 'travis/analyze.sh'], cwd=checkout)


def BuildLinuxAndroidx86(api):
  for x86_variant, abi in [('x64', 'x86_64'), ('x86', 'x86')]:
    RunGN(api, '--android', '--android-cpu=' + x86_variant)
    out_dir = 'android_debug_' + x86_variant
    Build(api, out_dir)
    UploadArtifacts(api, 'android-' + x86_variant, [
      'build/android/ant/chromium-debug.keystore',
      'out/%s/apks/SkyShell.apk' % out_dir,
      ('out/%s/gen/sky/shell/shell/shell/libs/%s/libsky_shell.so' %
       (out_dir, abi)),
      'out/%s/icudtl.dat' % out_dir,
      'out/%s/gen/sky/shell/shell/classes.dex.jar' % out_dir,
    ])


def AddPathPrefix(api, prefix, paths):
  return map(lambda path: api.path.join(prefix, path), paths)


def BuildLinuxAndroidArm(api):
  out_paths = [
    'apks/SkyShell.apk',
    'flutter.jar',
    'flutter.mojo',
    'gen/sky/shell/shell/shell/libs/armeabi-v7a/libsky_shell.so',
    'icudtl.dat',
    'gen/sky/shell/shell/classes.dex.jar',
  ]
  RunGN(api, '--android', '--enable-gcm')
  Build(api, 'android_debug', ':dist', 'gcm')
  UploadArtifacts(api, 'android-arm', [
    'build/android/ant/chromium-debug.keystore',
  ] + AddPathPrefix(api, 'out/android_debug', out_paths))

  # Build and upload engines for the runtime modes that use AOT compilation.
  for runtime_mode in ['profile', 'release']:
    build_output_dir = 'android_' + runtime_mode
    upload_dir = 'android-arm-' + runtime_mode

    RunGN(api, '--android', '--runtime-mode=' + runtime_mode)
    Build(api, build_output_dir)

    UploadArtifacts(api, upload_dir, [
      'build/android/ant/chromium-debug.keystore',
      'dart/runtime/bin/dart_io_entries.txt',
      'sky/engine/bindings/dart_vm_entry_points.txt',
      'sky/engine/bindings/dart_vm_entry_points_android.txt',
    ] + AddPathPrefix(api, 'out/%s' % build_output_dir, out_paths))

    # Upload artifacts used for AOT compilation on Linux hosts.
    UploadArtifacts(api, upload_dir, [
      'out/%s/clang_x86/gen_snapshot' % build_output_dir,
    ], archive_name='linux-x64.zip')

  UploadDartPackage(api, 'sky_engine')
  UploadDartPackage(api, 'sky_services')

  def UploadService(name, out_dir):
    def Upload(from_path, to_path):
      api.gsutil.upload(from_path, BUCKET_NAME, GetCloudPath(api, to_path),
          name='upload %s' % api.path.basename(to_path))

    def ServicesOut(path):
      checkout = api.path['checkout']
      return checkout.join('%s/%s' % (out_dir, path))

    dex_jar = '%s/%s_lib.dex.jar' % (name, name)
    interfaces_jar = '%s/interfaces_java.dex.jar' % (name)
    Upload(ServicesOut(dex_jar), dex_jar)
    Upload(ServicesOut(interfaces_jar), interfaces_jar)

  UploadService('gcm', 'out/android_debug/gen/third_party')


def BuildLinux(api):
  RunGN(api)
  Build(api, 'host_debug')
  UploadArtifacts(api, 'linux-x64', [
    'out/host_debug/flutter.mojo',
    'out/host_debug/icudtl.dat',
    'out/host_debug/sky_shell',
    'out/host_debug/sky_snapshot',
  ])


def TestObservatory(api):
  checkout = api.path['checkout']
  sky_shell_path = checkout.join('out/host_debug/sky_shell')
  empty_main_path = \
      checkout.join('sky/shell/testing/observatory/empty_main.dart')
  test_path = checkout.join('sky/shell/testing/observatory/test.dart')
  test_cmd = ['dart', test_path, sky_shell_path, empty_main_path]
  api.step('test observatory and service protocol', test_cmd, cwd=checkout)


def BuildMac(api):
  RunGN(api, '--runtime-mode', 'debug')
  RunGN(api, '--runtime-mode', 'profile', '--android')
  RunGN(api, '--runtime-mode', 'release', '--android')

  Build(api, 'host_debug')
  Build(api, 'android_profile', 'sky/engine/bindings:snapshot_cc')
  Build(api, 'android_release', 'sky/engine/bindings:snapshot_cc')

  UploadArtifacts(api, 'darwin-x64', [
    'out/host_debug/sky_snapshot',
    'out/host_debug/sky_shell',
    'out/host_debug/icudtl.dat',
  ])

  UploadArtifacts(api, "android-arm-profile" , [
    'out/android_profile/clang_i386/gen_snapshot',
  ], archive_name='darwin-x64.zip')

  UploadArtifacts(api, "android-arm-release" , [
    'out/android_release/clang_i386/gen_snapshot',
  ], archive_name='darwin-x64.zip')


def PackageIOSVariant(api, label, device_out, sim_out, bucket_name):
  checkout = api.path['checkout']
  out_dir = checkout.join('out')

  label_dir = out_dir.join(label)
  create_ios_framework_cmd = [
    checkout.join('sky/tools/create_ios_framework.py'),
    '--dst',
    label_dir,
    '--device-out-dir',
    api.path.join(out_dir, device_out),
    '--simulator-out-dir',
    api.path.join(out_dir, sim_out),
  ]
  api.step('Create iOS %s Flutter.framework' % label,
    create_ios_framework_cmd, cwd=checkout)

  # Zip Flutter.framework and upload it to cloud storage:
  api.zip.directory('Archive Flutter.framework for %s' % label,
    label_dir.join('Flutter.framework'),
    label_dir.join('Flutter.framework.zip'))

  # Zip the Xcode project and upload it to cloud storage:
  api.zip.directory('Archive FlutterXcode %s' % label,
    out_dir.join(device_out, 'Flutter'),
    label_dir.join('FlutterXcode.zip'))

  UploadArtifacts(api, bucket_name, [
    'dart/runtime/bin/dart_io_entries.txt',
    'sky/engine/bindings/dart_vm_entry_points.txt',
    'sky/engine/bindings/snapshot.dart',
    'out/%s/clang_x64/gen_snapshot' % device_out,
    'out/%s/Flutter.framework.zip' % label,
    'out/%s/FlutterXcode.zip' % label,
  ])


def BuildIOS(api):
  # Generate Ninja files for all valid configurations.
  RunGN(api, '--ios', '--runtime-mode', 'debug')
  RunGN(api, '--ios', '--runtime-mode', 'profile')
  RunGN(api, '--ios', '--runtime-mode', 'release')
  RunGN(api, '--ios', '--runtime-mode', 'debug', '--simulator')

  # Build all configurations.
  Build(api, 'ios_debug_sim')
  Build(api, 'ios_debug')
  Build(api, 'ios_profile')
  Build(api, 'ios_release')

  # Package all variants
  PackageIOSVariant(api,
      'debug',   'ios_debug',   'ios_debug_sim', 'ios')
  PackageIOSVariant(api,
      'profile', 'ios_profile', 'ios_debug_sim', 'ios-profile')
  PackageIOSVariant(api,
      'release', 'ios_release', 'ios_debug_sim', 'ios-release')


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
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmcontents('everything', api.path['slave_build'])

  GetCheckout(api)

  checkout = api.path['checkout']
  dart_bin = checkout.join('third_party', 'dart-sdk', 'dart-sdk', 'bin')
  env = { 'PATH': api.path.pathsep.join((str(dart_bin), '%(PATH)s')) }

  # The context adds dart to the path, only needed for the analyze step for now.
  with api.step.context({'env': env}):
    AnalyzeDartUI(api)

    api.step('download android tools',
      [checkout.join('tools/android/download_android_tools.py')])

    if api.platform.is_linux:
      BuildLinux(api)
      TestObservatory(api)
      BuildLinuxAndroidArm(api)
      BuildLinuxAndroidx86(api)

    if api.platform.is_mac:
      BuildMac(api)
      BuildIOS(api)


def GenTests(api):
  # A valid commit to flutter/engine, to make the gsutil urls look real.
  for platform in ('mac', 'linux'):
    yield (api.test(platform) + api.platform(platform, 64)
        + api.properties(mastername='client.flutter',
              buildername='%s Engine' % platform.capitalize(),
              slavename='fake-m1', clobber=''))

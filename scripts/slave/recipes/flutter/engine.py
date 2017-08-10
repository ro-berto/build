# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib

DEPS = [
  'build',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
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
  checkout = api.path['start_dir'].join('src')
  build_dir = checkout.join('out/%s' % config)
  ninja_args = ['ninja', '-C', build_dir]
  ninja_args.extend(targets)
  api.step('build %s' % ' '.join([config] + list(targets)), ninja_args)


def RunHostTests(api, out_dir, exe_extension=''):
  directory = api.path['start_dir'].join('src', out_dir)
  with api.context(cwd=directory):
    if api.platform.is_mac:
      api.step('Test Flutter Channels',
        [directory.join('flutter_channels_unittests' + exe_extension)])
    api.step('Test FTL',
      [directory.join('ftl_unittests' + exe_extension)])
    # TODO(goderbauer): enable these tests on Windows when they pass.
    if not api.platform.is_win:
      api.step('Test FML', [
        directory.join('fml_unittests' + exe_extension),
        '--gtest_filter="-*TimeSensitiveTest*"'
      ])
      api.step('Test Synchronization',
        [directory.join('synchronization_unittests' + exe_extension)])
      api.step('Test WTF',
        [directory.join('wtf_unittests' + exe_extension)])


def RunGN(api, *args):
  checkout = api.path['start_dir'].join('src')
  gn_cmd = ['python', checkout.join('flutter/tools/gn')]
  gn_cmd.extend(args)
  api.step('gn %s' % ' '.join(args), gn_cmd)


def AddFiles(api, pkg, relative_paths):
  for path in relative_paths:
    pkg.add_file(pkg.root.join(path), archive_name=api.path.basename(path))


def UploadArtifacts(api, platform, file_paths, archive_name='artifacts.zip'):
  dir_label = '%s UploadArtifacts %s' % (platform, archive_name)
  with MakeTempDir(api, dir_label) as temp_dir:
    local_zip = temp_dir.join('artifacts.zip')
    remote_name = '%s/%s' % (platform, archive_name)
    remote_zip = GetCloudPath(api, remote_name)
    pkg = api.zip.make_package(api.path['start_dir'].join('src'), local_zip)
    AddFiles(api, pkg, file_paths)

    pkg.zip('Zip %s %s' % (platform, archive_name))
    api.gsutil.upload(local_zip, BUCKET_NAME, remote_zip,
        name='upload "%s"' % remote_name)


def UploadFolder(api, dir_label, parent_dir, folder_name, zip_name):
  with MakeTempDir(api, dir_label) as temp_dir:
    local_zip = temp_dir.join(zip_name)
    remote_name = zip_name
    remote_zip = GetCloudPath(api, remote_name)
    parent_dir = api.path['start_dir'].join(parent_dir)
    pkg = api.zip.make_package(parent_dir, local_zip)
    pkg.add_directory(parent_dir.join(folder_name))
    pkg.zip('Zip %s' % folder_name)
    api.gsutil.upload(local_zip, BUCKET_NAME, remote_zip,
        name='upload %s' % remote_name)


def UploadDartPackage(api, package_name):
  UploadFolder(api,
    'UploadDartPackage %s' % package_name, # dir_label
    'src/out/android_debug/dist/packages', # parent_dir
    package_name, # folder_name
    "%s.zip" % package_name) # zip_name


def UploadFlutterPatchedSdk(api):
  UploadFolder(api,
    'Upload Flutter patched sdk', # dir_label
    'src/out/host_debug_unopt', # parent_dir
    'flutter_patched_sdk', # folder_name
    'flutter_patched_sdk.zip') # zip_name

def UploadDartSdk(api, archive_name):
  UploadFolder(api,
    'Upload Dart SDK', # dir_label
    'src/out/host_debug_unopt', # parent_dir
    'dart-sdk', # folder_name
    archive_name)

# TODO(eseidel): Would be nice to have this on api.path or api.file.
@contextlib.contextmanager
def MakeTempDir(api, label):
  try:
    temp_dir = api.path.mkdtemp('tmp')
    yield temp_dir
  finally:
    api.file.rmtree('temp dir for %s' % label, temp_dir)


def AnalyzeDartUI(api):
  RunGN(api, '--unoptimized')
  Build(api, 'host_debug_unopt', 'generate_dart_ui')

  checkout = api.path['start_dir'].join('src')
  with api.context(cwd=checkout):
    api.step('analyze dart_ui', ['/bin/sh', 'flutter/travis/analyze.sh'])


def BuildLinuxAndroidx86(api):
  for x86_variant in ['x64', 'x86']:
    RunGN(api, '--android', '--android-cpu=' + x86_variant)
    out_dir = 'android_debug_' + x86_variant
    Build(api, out_dir)
    folder = 'android-' + x86_variant
    UploadArtifacts(api, folder, [
      'out/%s/flutter.jar' % out_dir,
      'out/%s/lib.stripped/libflutter.so' % out_dir,
    ])
    UploadArtifacts(api, folder, [
      'out/%s/libflutter.so' % out_dir
    ], archive_name='symbols.zip')


def AddPathPrefix(api, prefix, paths):
  return map(lambda path: api.path.join(prefix, path), paths)


def BuildLinuxAndroidArm(api):
  out_paths = [
    'flutter.jar',
  ]
  RunGN(api, '--android')
  Build(api, 'android_debug')
  Build(api, 'android_debug', ':dist')
  UploadArtifacts(api, 'android-arm',
                  AddPathPrefix(api, 'out/android_debug', out_paths))
  UploadArtifacts(api, 'android-arm', [
      'out/android_debug/libflutter.so'
  ], archive_name='symbols.zip')

  # Build and upload engines for the runtime modes that use AOT compilation.
  for runtime_mode in ['profile', 'release']:
    build_output_dir = 'android_' + runtime_mode
    upload_dir = 'android-arm-' + runtime_mode

    RunGN(api, '--android', '--runtime-mode=' + runtime_mode)
    Build(api, build_output_dir)

    UploadArtifacts(api, upload_dir, [
      'dart/runtime/bin/dart_io_entries.txt',
      'flutter/runtime/dart_vm_entry_points.txt',
    ] + AddPathPrefix(api, 'out/%s' % build_output_dir, out_paths))

    # Upload artifacts used for AOT compilation on Linux hosts.
    UploadArtifacts(api, upload_dir, [
      'out/%s/clang_x86/gen_snapshot' % build_output_dir,
    ], archive_name='linux-x64.zip')
    UploadArtifacts(api, upload_dir, [
        'out/%s/libflutter.so' % build_output_dir
    ], archive_name='symbols.zip')

  UploadDartPackage(api, 'sky_engine')


def BuildLinux(api):
  RunGN(api, '--unoptimized')
  RunGN(api, '--runtime-mode', 'release', '--android', '--enable-vulkan')
  Build(api, 'host_debug_unopt')
  Build(api, 'android_release_vulkan')
  RunHostTests(api, 'out/host_debug_unopt')
  UploadArtifacts(api, 'linux-x64', [
    'out/host_debug_unopt/icudtl.dat',
    'out/host_debug_unopt/flutter_tester',
    'out/host_debug_unopt/gen/flutter/lib/snapshot/isolate_snapshot.bin',
    'out/host_debug_unopt/gen/flutter/lib/snapshot/vm_isolate_snapshot.bin',
  ])
  UploadFlutterPatchedSdk(api)
  UploadDartSdk(api, archive_name='dart-sdk-linux-x64.zip')


def TestObservatory(api):
  checkout = api.path['start_dir'].join('src')
  flutter_tester_path = checkout.join('out/host_debug_unopt/flutter_tester')
  empty_main_path = \
      checkout.join('flutter/shell/testing/observatory/empty_main.dart')
  test_path = checkout.join('flutter/shell/testing/observatory/test.dart')
  test_cmd = ['dart', test_path, flutter_tester_path, empty_main_path]
  with api.context(cwd=checkout):
    api.step('test observatory and service protocol', test_cmd)


def TestEngine(api):
  checkout = api.path['start_dir'].join('src')
  test_cmd = [checkout.join('flutter/testing/run_tests.sh')]
  with api.context(cwd=checkout):
    api.step('engine unit tests', test_cmd)


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
  ios_tools_path = api.path['start_dir'].join('src', 'ios_tools')
  target_version = '8.0'
  xcode_json = RunFindXcode(api, ios_tools_path, target_version)
  if not xcode_json['matches']:
    raise api.step.StepFailure('Xcode %s not found' % target_version)


def BuildMac(api):
  RunGN(api, '--runtime-mode', 'debug', '--unoptimized')
  RunGN(api, '--runtime-mode', 'profile', '--android')
  RunGN(api, '--runtime-mode', 'release', '--android')
  RunGN(api, '--runtime-mode', 'release', '--android', '--enable-vulkan')

  Build(api, 'host_debug_unopt')
  RunHostTests(api, 'out/host_debug_unopt')

  Build(api, 'android_profile', 'flutter/lib/snapshot')
  Build(api, 'android_release', 'flutter/lib/snapshot')
  Build(api, 'android_release_vulkan')

  UploadArtifacts(api, 'darwin-x64', [
    'out/host_debug_unopt/icudtl.dat',
    'out/host_debug_unopt/flutter_tester',
    'out/host_debug_unopt/gen/flutter/lib/snapshot/isolate_snapshot.bin',
    'out/host_debug_unopt/gen/flutter/lib/snapshot/vm_isolate_snapshot.bin',
  ])

  UploadArtifacts(api, "android-arm-profile" , [
    'out/android_profile/clang_i386/gen_snapshot',
  ], archive_name='darwin-x64.zip')

  UploadArtifacts(api, "android-arm-release" , [
    'out/android_release/clang_i386/gen_snapshot',
  ], archive_name='darwin-x64.zip')

  UploadDartSdk(api, archive_name='dart-sdk-darwin-x64.zip')


def PackageIOSVariant(api, label, device_out, sim_out, bucket_name):
  checkout = api.path['start_dir'].join('src')
  out_dir = checkout.join('out')

  label_dir = out_dir.join(label)
  create_ios_framework_cmd = [
    checkout.join('flutter/sky/tools/create_ios_framework.py'),
    '--dst',
    label_dir,
    '--device-out-dir',
    api.path.join(out_dir, device_out),
    '--simulator-out-dir',
    api.path.join(out_dir, sim_out),
  ]
  with api.context(cwd=checkout):
    api.step('Create iOS %s Flutter.framework' % label,
      create_ios_framework_cmd)

  # Zip Flutter.framework and upload it to cloud storage:
  api.zip.directory('Archive Flutter.framework for %s' % label,
    label_dir.join('Flutter.framework'),
    label_dir.join('Flutter.framework.zip'))

  UploadArtifacts(api, bucket_name, [
    'dart/runtime/bin/dart_io_entries.txt',
    'flutter/runtime/dart_vm_entry_points.txt',
    'flutter/lib/snapshot/snapshot.dart',
    'flutter/shell/platform/darwin/ios/framework/Flutter.podspec',
    'out/%s/clang_x64/gen_snapshot' % device_out,
    'out/%s/Flutter.framework.zip' % label,
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


def BuildWindows(api):
  RunGN(api, '--runtime-mode', 'debug', '--unoptimized')
  RunGN(api, '--runtime-mode', 'profile', '--android')
  RunGN(api, '--runtime-mode', 'release', '--android')

  Build(api, 'host_debug_unopt',
    'flutter/lib/snapshot:generate_snapshot_bin', 'lib/ftl:ftl_unittests',
    'dart:create_sdk')
  Build(api, 'android_profile', 'gen_snapshot')
  Build(api, 'android_release', 'gen_snapshot')

  RunHostTests(api, 'out\\host_debug_unopt', '.exe')

  UploadArtifacts(api, 'windows-x64', [
    'out/host_debug_unopt/gen/flutter/lib/snapshot/isolate_snapshot.bin',
    'out/host_debug_unopt/gen/flutter/lib/snapshot/vm_isolate_snapshot.bin',
  ])

  UploadArtifacts(api, "android-arm-profile" , [
    'out/android_profile/gen_snapshot.exe',
  ], archive_name='windows-x64.zip')

  UploadArtifacts(api, "android-arm-release" , [
    'out/android_release/gen_snapshot.exe',
  ], archive_name='windows-x64.zip')

  UploadDartSdk(api, archive_name='dart-sdk-windows-x64.zip')


def BuildJavadoc(api):
  checkout = api.path['start_dir'].join('src')
  with MakeTempDir(api, 'BuildJavadoc') as temp_dir:
    javadoc_cmd = [checkout.join('flutter/tools/gen_javadoc.py'),
                   '--out-dir', temp_dir]
    with api.context(cwd=checkout):
      api.step('build javadoc', javadoc_cmd)
    api.zip.directory('archive javadoc', temp_dir,
                      checkout.join('out/android_javadoc.zip'))

  api.gsutil.upload(checkout.join('out/android_javadoc.zip'),
                    BUCKET_NAME,
                    GetCloudPath(api, 'android-javadoc.zip'),
                    name='upload javadoc')


def BuildObjcDoc(api):
  """Builds documentation for the Objective-C variant of engine."""
  checkout = api.path['start_dir'].join('src')
  with MakeTempDir(api, 'BuildObjcDoc') as temp_dir:
    objcdoc_cmd = [checkout.join('flutter/tools/gen_objcdoc.sh'), temp_dir]
    with api.context(cwd=checkout.join('flutter')):
      api.step('build obj-c doc', objcdoc_cmd)
    api.zip.directory('archive obj-c doc', temp_dir,
                      checkout.join('out/ios-objcdoc.zip'))

  api.gsutil.upload(checkout.join('out/ios-objcdoc.zip'),
                    BUCKET_NAME,
                    GetCloudPath(api, 'ios-objcdoc.zip'),
                    name='upload obj-c doc')


def GetCheckout(api):
  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = 'src/flutter'
  soln.url = \
      'https://chromium.googlesource.com/external/github.com/flutter/engine'
  # TODO(eseidel): What does parent_got_revision_mapping do?  Do I care?
  src_cfg.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'
  src_cfg.target_os = set(['android'])
  api.gclient.c = src_cfg
  api.gclient.c.got_revision_mapping['src/flutter'] = 'got_engine_revision'
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()


def RunSteps(api):
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmcontents('everything', api.path['start_dir'])

  GetCheckout(api)

  checkout = api.path['start_dir'].join('src')
  dart_bin = checkout.join('dart', 'tools', 'sdks', 'linux', 'dart-sdk', 'bin')
  env = { 'PATH': api.path.pathsep.join((str(dart_bin), '%(PATH)s')) }

  # The context adds dart to the path, only needed for the analyze step for now.
  with api.context(env=env):

    if api.platform.is_linux:
      AnalyzeDartUI(api)
      BuildLinux(api)
      TestObservatory(api)
      TestEngine(api)
      BuildLinuxAndroidArm(api)
      BuildLinuxAndroidx86(api)
      BuildJavadoc(api)

    if api.platform.is_mac:
      SetupXcode(api)
      BuildMac(api)
      BuildIOS(api)
      BuildObjcDoc(api)

    if api.platform.is_win:
      BuildWindows(api)


def GenTests(api):
  # A valid commit to flutter/engine, to make the gsutil urls look real.
  for platform in ('mac', 'linux', 'win'):
    test = (api.test(platform) + api.platform(platform, 64)
        + api.properties(mastername='client.flutter',
              buildername='%s Engine' % platform.capitalize(),
              bot_id='fake-m1', clobber=''))
    if platform == 'mac':
      test += (
        api.step_data('set_xcode_version', api.json.output({
          'matches': {
            '/Applications/Xcode8.0.app': '8.0 (8A218a)'
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

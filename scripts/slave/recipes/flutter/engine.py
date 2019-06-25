# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
import contextlib

DEPS = [
  'build',
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'depot_tools/gsutil',
  'depot_tools/osx_sdk',
  'goma',
  'recipe_engine/buildbucket',
  'recipe_engine/cipd',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'recipe_engine/python',
  'zip',
]

BUCKET_NAME = 'flutter_infra'
ICU_DATA_PATH = 'third_party/icu/flutter/icudtl.dat'
GIT_REPO = 'https://chromium.googlesource.com/external/github.com/flutter/engine' # pylint: disable=line-too-long

def GetCloudPath(api, path):
  git_hash = api.buildbucket.gitiles_commit.id
  if api.runtime.is_experimental:
    return 'flutter/experimental/%s/%s' % (git_hash, path)
  return 'flutter/%s/%s' % (git_hash, path)


def Build(api, config, *targets):
  checkout = api.path['start_dir'].join('src')
  build_dir = checkout.join('out/%s' % config)
  goma_jobs = api.properties['goma_jobs']
  ninja_args = [api.depot_tools.ninja_path, '-j', goma_jobs, '-C', build_dir]
  ninja_args.extend(targets)
  api.goma.build_with_goma(
    name='build %s' % ' '.join([config] + list(targets)),
    ninja_command=ninja_args)


def RunHostTests(api, out_dir, exe_extension=''):
  directory = api.path['start_dir'].join('src', out_dir)
  with api.context(cwd=directory):
    # Only run flow gold tests on Linux
    flow_gold_args = ["--gtest_filter=-PerformanceOverlayLayer.Gold"]
    if api.platform.is_linux:
      flow_gold_args = [
        '--golden-dir=%s' %
          api.path['start_dir'].join('src', 'flutter', 'testing', 'resources'),
        '--font-file=%s' %
          api.path['start_dir'].join('src', 'flutter', 'third_party', 'txt',
                                     'third_party', 'fonts',
                                     'Roboto-Regular.ttf')
      ]
    api.step('Test Flow',
      [directory.join('flow_unittests' + exe_extension)] + flow_gold_args)

    # Cross platform tests.
    api.step('Test FML', [
      directory.join('fml_unittests' + exe_extension),
      '--gtest_filter="-*TimeSensitiveTest*"'
    ])
    api.step('Test Runtime',
      [directory.join('runtime_unittests' + exe_extension)])
    api.step('Test Shell',
      [directory.join('shell_unittests' + exe_extension)])

    if not api.platform.is_win:
      api.step('Test Embedder API',
        [directory.join('embedder_unittests' + exe_extension)])

    if api.platform.is_mac:
      api.step('Test Flutter Channels',
        [directory.join('flutter_channels_unittests' + exe_extension)])

def RunGN(api, *args):
  # flutter/tools/gn assumes access to depot_tools on path for `ninja`.
  with api.depot_tools.on_path():
    checkout = api.path['start_dir'].join('src')
    gn_cmd = ['python', checkout.join('flutter/tools/gn'), '--goma']
    gn_cmd.extend(args)
    api.step('gn %s' % ' '.join(args), gn_cmd)


# The relative_paths parameter is a list of strings and pairs of strings.
# If the path is a string, then it will be used as the source filename,
# and its basename will be used as the destination filename in the archive.
# If the path is a pair, then the first element will be used as the source
# filename, and the second element will be used as the destination filename
# in the archive.
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


def UploadFolder(api, dir_label, parent_dir, folder_name, zip_name,
                 platform=None):
  with MakeTempDir(api, dir_label) as temp_dir:
    local_zip = temp_dir.join(zip_name)
    if platform is None:
      remote_name = zip_name
    else:
      remote_name = '%s/%s' % (platform, zip_name)
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
    'src/out/host_debug', # parent_dir
    'flutter_patched_sdk', # folder_name
    'flutter_patched_sdk.zip') # zip_name

  host_release_path = api.path['start_dir'].join('src/out/host_release')
  api.file.move(
    'Move release flutter_patched_sdk to flutter_patched_sdk_product',
    host_release_path.join('flutter_patched_sdk'),
    host_release_path.join('flutter_patched_sdk_product'))
  UploadFolder(api,
    'Upload Product Flutter patched sdk', # dir_label
    'src/out/host_release', # parent_dir
    'flutter_patched_sdk_product', # folder_name
    'flutter_patched_sdk_product.zip') # zip_name

def UploadDartSdk(api, archive_name):
  UploadFolder(api,
    'Upload Dart SDK', # dir_label
    'src/out/host_debug', # parent_dir
    'dart-sdk', # folder_name
    archive_name)

def UploadWebSdk(api, archive_name):
  UploadFolder(api,
    'Upload Web SDK', # dir_label
    'src/out/host_debug', # parent_dir
    'flutter_web_sdk', # folder_name
    archive_name)

# TODO(eseidel): Would be nice to have this on api.path or api.file.
@contextlib.contextmanager
def MakeTempDir(api, label):
  temp_dir = api.path.mkdtemp('tmp')
  try:
    yield temp_dir
  finally:
    api.file.rmtree('temp dir for %s' % label, temp_dir)


def AnalyzeDartUI(api):
  RunGN(api, '--unoptimized')
  Build(api, 'host_debug_unopt', 'generate_dart_ui')

  checkout = api.path['start_dir'].join('src')
  with api.context(cwd=checkout):
    api.step('analyze dart_ui', ['/bin/bash', 'flutter/ci/analyze.sh'])


def VerifyExportedSymbols(api):
  checkout = api.path['start_dir'].join('src')
  out_dir = checkout.join('out')
  script_dir = checkout.join('flutter/testing/symbols')
  script_path = script_dir.join('verify_exported.dart')
  with api.context(cwd=script_dir):
    api.step('pub get for verify_exported.dart', ['pub', 'get'])
  api.step('Verify exported symbols on release binaries', [
      'dart', script_path, out_dir])


def UploadTreeMap(api, upload_dir, lib_flutter_path, android_triple):
  with MakeTempDir(api, 'treemap') as temp_dir:
    checkout = api.path['start_dir'].join('src')
    script_path = checkout.join(
        'third_party/dart/runtime/'
        'third_party/binary_size/src/run_binary_size_analysis.py')
    library_path = checkout.join(lib_flutter_path)
    destionation_dir = temp_dir.join('sizes')
    addr2line = checkout.join(
        'third_party/android_tools/ndk/toolchains/' + android_triple +
        '-4.9/prebuilt/linux-x86_64/bin/' + android_triple + '-addr2line')
    args = [
        '--library', library_path, '--destdir', destionation_dir,
        "--addr2line-binary", addr2line ]

    api.python('generate treemap for %s' % upload_dir, script_path, args)

    remote_name = GetCloudPath(api, upload_dir)
    result = api.gsutil.upload(destionation_dir, BUCKET_NAME, remote_name,
        args=['-r'], name='upload treemap for %s' % lib_flutter_path,
                               link_name=None)
    result.presentation.links['Open Treemap'] = (
        'https://storage.googleapis.com/%s/%s/sizes/index.html' % (
            BUCKET_NAME, remote_name))


def BuildLinuxAndroid(api):
  if api.properties.get('build_android_debug', True):
    debug_variants = [
      ('arm', 'android_debug', 'android-arm'),
      ('arm64', 'android_debug_arm64', 'android-arm64'),
      ('x86', 'android_debug_x86', 'android-x86'),
      ('x64', 'android_debug_x64', 'android-x64'),
    ]
    for android_cpu, out_dir, artifact_dir in debug_variants:
      RunGN(api, '--android', '--android-cpu=%s' % android_cpu, '--no-lto')
      Build(api, out_dir)
      artifacts = ['out/%s/flutter.jar' % out_dir]
      if android_cpu in ['x86', 'x64']:
          artifacts.append('out/%s/lib.stripped/libflutter.so' % out_dir)
      UploadArtifacts(api, artifact_dir, artifacts)
      UploadArtifacts(api, artifact_dir, ['out/%s/libflutter.so' % out_dir],
                      archive_name='symbols.zip')
    Build(api, 'android_debug', ':dist')
    UploadDartPackage(api, 'sky_engine')
    BuildJavadoc(api)

  if api.properties.get('build_android_vulkan', True):
    RunGN(api, '--runtime-mode', 'release', '--android', '--enable-vulkan')
    Build(api, 'android_release_vulkan')

  if api.properties.get('build_android_aot', True):
    # Build and upload engines for the runtime modes that use AOT compilation.
    aot_variants = [
      ('arm', 'android_%s', 'android-arm-%s', 'clang_x86',
      'arm-linux-androideabi'),
      ('arm64', 'android_%s_arm64', 'android-arm64-%s', 'clang_x64',
      'aarch64-linux-android'),
    ]
    for (android_cpu, out_dir, artifact_dir, clang_dir,
        android_triple) in aot_variants:
      for runtime_mode in ['profile', 'release']:
        build_output_dir = out_dir % runtime_mode
        upload_dir = artifact_dir % runtime_mode

        RunGN(api, '--android', '--runtime-mode=' + runtime_mode,
              '--android-cpu=%s' % android_cpu)
        Build(api, build_output_dir)

        UploadArtifacts(api, upload_dir, [
          'out/%s/flutter.jar' % build_output_dir,
        ])

        # Upload artifacts used for AOT compilation on Linux hosts.
        UploadArtifacts(api, upload_dir, [
          'out/%s/%s/gen_snapshot' % (build_output_dir, clang_dir),
        ], archive_name='linux-x64.zip')
        unstripped_lib_flutter_path = 'out/%s/libflutter.so' % build_output_dir
        UploadArtifacts(api, upload_dir, [
            unstripped_lib_flutter_path
        ], archive_name='symbols.zip')

        if runtime_mode == 'release':
          UploadTreeMap(
              api, upload_dir, unstripped_lib_flutter_path, android_triple)


def BuildLinux(api):
  RunGN(api, '--runtime-mode', 'debug', '--full-dart-sdk')
  RunGN(api, '--runtime-mode', 'debug', '--unoptimized')
  RunGN(api, '--runtime-mode', 'release')
  Build(api, 'host_debug_unopt')
  Build(api, 'host_debug')
  Build(api, 'host_release')
  RunHostTests(api, 'out/host_debug_unopt')
  UploadArtifacts(api, 'linux-x64', [
    ICU_DATA_PATH,
    'out/host_debug_unopt/flutter_tester',
    'out/host_debug_unopt/gen/flutter/lib/snapshot/isolate_snapshot.bin',
    'out/host_debug_unopt/gen/flutter/lib/snapshot/vm_isolate_snapshot.bin',
    'out/host_debug_unopt/gen/frontend_server.dart.snapshot',
  ])
  UploadArtifacts(api, 'linux-x64', [
    'out/host_debug/flutter_embedder.h',
    'out/host_debug/libflutter_engine.so',
  ], archive_name='linux-x64-embedder')

  UploadArtifacts(api, 'linux-x64', [
    'out/host_debug/flutter_export.h',
    'out/host_debug/flutter_glfw.h',
    'out/host_debug/flutter_messenger.h',
    'out/host_debug/flutter_plugin_registrar.h',
    'out/host_debug/libflutter_linux.so',
  ], archive_name='linux-x64-flutter.zip')
  UploadFolder(api,
    'Upload linux-x64 Flutter library C++ wrapper',
    'src/out/host_debug',
    'cpp_client_wrapper',
    'flutter-cpp-client-wrapper.zip',
    'linux-x64')

  UploadFlutterPatchedSdk(api)
  UploadDartSdk(api, archive_name='dart-sdk-linux-x64.zip')
  UploadWebSdk(api, archive_name='flutter-web-sdk-linux-x64.zip')


def BuildFuchsia(api):
  if api.properties.get('build_host', True):
    RunGN(api, '--runtime-mode', 'debug', '--fuchsia')
    RunGN(api, '--runtime-mode', 'profile', '--fuchsia')
    RunGN(api, '--runtime-mode', 'release', '--fuchsia')
    Build(api, 'fuchsia_debug')
    Build(api, 'fuchsia_profile')
    Build(api, 'fuchsia_release')
    # TODO(cbracken): build and upload CIPD package


def TestObservatory(api):
  checkout = api.path['start_dir'].join('src')
  flutter_tester_path = checkout.join('out/host_debug_unopt/flutter_tester')
  empty_main_path = \
      checkout.join('flutter/shell/testing/observatory/empty_main.dart')
  test_path = checkout.join('flutter/shell/testing/observatory/test.dart')
  test_cmd = ['dart', test_path, flutter_tester_path, empty_main_path]
  with api.context(cwd=checkout):
    api.step('test observatory and service protocol', test_cmd)


#def TestEngine(api):
#  checkout = api.path['start_dir'].join('src')
#  test_cmd = [checkout.join('flutter/testing/run_tests.sh')]
#  with api.context(cwd=checkout):
#    api.step('engine unit tests', test_cmd)

def GetMacSDKDir(api):
  return api.path['cache'].join('builder', 'mac_sdk')

@contextmanager
def SetupXcode(api):
  macos_sdk_cache_dir = GetMacSDKDir(api)
  api.cipd.ensure(macos_sdk_cache_dir, api.cipd.EnsureFile()
    .add_package('flutter_internal/macos/sdk', 'version:10.13')
  )

  # See cr-buildbucket.cfg for how the version is passed in.
  # https://github.com/flutter/infra/blob/master/config/cr-buildbucket.cfg#L148
  with api.osx_sdk('ios'):
    yield

def BuildMac(api):
  if api.properties.get('build_host', True):
    RunGN(api, '--runtime-mode', 'debug', '--no-lto', '--full-dart-sdk',
               '--mac-sdk-path', str(GetMacSDKDir(api)))
    RunGN(api, '--runtime-mode', 'debug', '--unoptimized', '--no-lto',
               '--mac-sdk-path', str(GetMacSDKDir(api)))
    Build(api, 'host_debug_unopt')
    Build(api, 'host_debug')
    RunHostTests(api, 'out/host_debug_unopt')
    host_debug_path = api.path['start_dir'].join('src', 'out', 'host_debug')

    api.zip.directory('Archive FlutterEmbedder.framework',
      host_debug_path.join('FlutterEmbedder.framework'),
      host_debug_path.join('FlutterEmbedder.framework.zip'))

    api.zip.directory('Archive FlutterMacOS.framework',
      host_debug_path.join('FlutterMacOS.framework'),
      host_debug_path.join('FlutterMacOS.framework.zip'))

    UploadArtifacts(api, 'darwin-x64', [
      ICU_DATA_PATH,
      'out/host_debug_unopt/flutter_tester',
      'out/host_debug_unopt/gen/flutter/lib/snapshot/isolate_snapshot.bin',
      'out/host_debug_unopt/gen/flutter/lib/snapshot/vm_isolate_snapshot.bin',
      'out/host_debug_unopt/gen/frontend_server.dart.snapshot',
    ])

    UploadArtifacts(api, 'darwin-x64', [
      'out/host_debug/FlutterEmbedder.framework.zip'
    ], archive_name='FlutterEmbedder.framework.zip')

    UploadArtifacts(api, 'darwin-x64', [
      'out/host_debug/FlutterMacOS.framework.zip',
      'flutter/shell/platform/darwin/macos/framework/FlutterMacOS.podspec',
    ], archive_name='FlutterMacOS.framework.zip')

    UploadDartSdk(api, archive_name='dart-sdk-darwin-x64.zip')
    UploadWebSdk(api, archive_name='flutter-web-sdk-darwin-x64.zip')

  if api.properties.get('build_android_vulkan', True):
    RunGN(api, '--runtime-mode', 'release', '--android', '--enable-vulkan',
               '--mac-sdk-path', str(GetMacSDKDir(api)))
    Build(api, 'android_release_vulkan')

  if api.properties.get('build_android_aot', True):
    RunGN(api, '--runtime-mode', 'profile', '--android',
               '--mac-sdk-path', str(GetMacSDKDir(api)))
    RunGN(api, '--runtime-mode', 'profile', '--android', '--android-cpu=arm64',
               '--mac-sdk-path', str(GetMacSDKDir(api)))
    RunGN(api, '--runtime-mode', 'release', '--android',
               '--mac-sdk-path', str(GetMacSDKDir(api)))
    RunGN(api, '--runtime-mode', 'release', '--android', '--android-cpu=arm64',
               '--mac-sdk-path', str(GetMacSDKDir(api)))

    Build(api, 'android_profile', 'flutter/lib/snapshot')
    Build(api, 'android_profile_arm64', 'flutter/lib/snapshot')
    Build(api, 'android_release', 'flutter/lib/snapshot')
    Build(api, 'android_release_arm64', 'flutter/lib/snapshot')

    UploadArtifacts(api, "android-arm-profile" , [
      'out/android_profile/clang_x86/gen_snapshot',
    ], archive_name='darwin-x64.zip')
    UploadArtifacts(api, "android-arm64-profile" , [
      'out/android_profile_arm64/clang_x64/gen_snapshot',
    ], archive_name='darwin-x64.zip')
    UploadArtifacts(api, "android-arm-release" , [
      'out/android_release/clang_x86/gen_snapshot',
    ], archive_name='darwin-x64.zip')
    UploadArtifacts(api, "android-arm64-release" , [
      'out/android_release_arm64/clang_x64/gen_snapshot',
    ], archive_name='darwin-x64.zip')

def PackageIOSVariant(api, label, arm64_out, armv7_out, sim_out, bucket_name):
  checkout = api.path['start_dir'].join('src')
  out_dir = checkout.join('out')

  # Package the multi-arch framework for iOS.
  label_dir = out_dir.join(label)
  create_ios_framework_cmd = [
    checkout.join('flutter/sky/tools/create_ios_framework.py'),
    '--dst',
    label_dir,
    '--arm64-out-dir',
    api.path.join(out_dir, arm64_out),
    '--armv7-out-dir',
    api.path.join(out_dir, armv7_out),
    '--simulator-out-dir',
    api.path.join(out_dir, sim_out),
  ]
  if label == 'release':
    create_ios_framework_cmd.extend([
      "--dsym",
      "--strip",
    ])
  with api.context(cwd=checkout):
    api.step('Create iOS %s Flutter.framework' % label,
      create_ios_framework_cmd)

  # Zip Flutter.framework.
  api.zip.directory('Archive Flutter.framework for %s' % label,
    label_dir.join('Flutter.framework'),
    label_dir.join('Flutter.framework.zip'))

  # Package the multi-arch gen_snapshot for macOS.
  create_macos_gen_snapshot_cmd = [
    checkout.join('flutter/sky/tools/create_macos_gen_snapshot.py'),
    '--dst',
    label_dir,
    '--arm64-out-dir',
    api.path.join(out_dir, arm64_out),
    '--armv7-out-dir',
    api.path.join(out_dir, armv7_out),
  ]

  with api.context(cwd=checkout):
    api.step('Create macOS %s gen_snapshot' % label,
      create_macos_gen_snapshot_cmd)

  # Upload the artifacts to cloud storage.
  artifacts = [
    'flutter/shell/platform/darwin/ios/framework/Flutter.podspec',
    'out/%s/gen_snapshot' % label,
    'out/%s/Flutter.framework.zip' % label,
  ]
  UploadArtifacts(api, bucket_name, artifacts)

  if label == 'release':
    dsym_zip = label_dir.join('Flutter.dSYM.zip')
    pkg = api.zip.make_package(label_dir, dsym_zip)
    pkg.add_directory(label_dir.join('Flutter.dSYM'))
    pkg.zip('Zip Flutter.dSYM')
    remote_name = '%s/Flutter.dSYM.zip' % bucket_name
    remote_zip = GetCloudPath(api, remote_name)
    api.gsutil.upload(dsym_zip, BUCKET_NAME, remote_zip,
        name='upload "%s"' % remote_name)


# def RunIOSTests(api):
#   directory = api.path['start_dir'].join('src', 'flutter', 'testing', 'ios',
#                                          'IosUnitTests')
#   with api.context(cwd=directory):
#     api.step('iOS Unit Tests', ["./run_tests.sh", "ios_debug_sim"])

def BuildIOS(api):
  # Generate Ninja files for all valid configurations.
  RunGN(api, '--ios', '--runtime-mode', 'debug', '--no-lto',
             '--mac-sdk-path', str(GetMacSDKDir(api)))
  RunGN(api, '--ios', '--runtime-mode', 'debug', '--ios-cpu=arm', '--no-lto',
             '--mac-sdk-path', str(GetMacSDKDir(api)))
  RunGN(api, '--ios', '--runtime-mode', 'debug', '--simulator', '--no-lto',
             '--mac-sdk-path', str(GetMacSDKDir(api)))
  RunGN(api, '--ios', '--runtime-mode', 'profile',
             '--mac-sdk-path', str(GetMacSDKDir(api)))
  RunGN(api, '--ios', '--runtime-mode', 'profile', '--ios-cpu=arm',
             '--mac-sdk-path', str(GetMacSDKDir(api)))
  RunGN(api, '--ios', '--runtime-mode', 'release',
             '--mac-sdk-path', str(GetMacSDKDir(api)))
  RunGN(api, '--ios', '--runtime-mode', 'release', '--ios-cpu=arm',
             '--mac-sdk-path', str(GetMacSDKDir(api)))

  # Build all configurations.
  Build(api, 'ios_debug_sim')
  # RunIOSTests(api)
  Build(api, 'ios_debug')
  Build(api, 'ios_debug_arm')
  Build(api, 'ios_profile')
  Build(api, 'ios_profile_arm')
  Build(api, 'ios_release')
  Build(api, 'ios_release_arm')

  # Package all variants
  PackageIOSVariant(api,
      'debug',   'ios_debug',   'ios_debug_arm',   'ios_debug_sim', 'ios')
  PackageIOSVariant(api,
      'profile', 'ios_profile', 'ios_profile_arm', 'ios_debug_sim',
                    'ios-profile')
  PackageIOSVariant(api,
      'release', 'ios_release', 'ios_release_arm', 'ios_debug_sim',
                    'ios-release')


def BuildWindows(api):
  if api.properties.get('build_host', True):
    RunGN(api, '--runtime-mode', 'debug', '--full-dart-sdk', '--no-lto')
    RunGN(api, '--runtime-mode', 'debug', '--unoptimized', '--no-lto')
    Build(api, 'host_debug_unopt')
    Build(api, 'host_debug')
    RunHostTests(api, 'out\\host_debug', '.exe')
    UploadArtifacts(api, 'windows-x64', [
      ICU_DATA_PATH,
      'out/host_debug/flutter_tester.exe',
      'out/host_debug/gen/flutter/lib/snapshot/isolate_snapshot.bin',
      'out/host_debug/gen/flutter/lib/snapshot/vm_isolate_snapshot.bin',
      'out/host_debug/gen/frontend_server.dart.snapshot',
    ])

    UploadArtifacts(api, 'windows-x64', [
      'out/host_debug/flutter_embedder.h',
      'out/host_debug/flutter_engine.dll',
      'out/host_debug/flutter_engine.dll.exp',
      'out/host_debug/flutter_engine.dll.lib',
      'out/host_debug/flutter_engine.dll.pdb',
    ], archive_name='windows-x64-embedder.zip')

    UploadArtifacts(api, 'windows-x64', [
      'out/host_debug/flutter_export.h',
      'out/host_debug/flutter_glfw.h',
      'out/host_debug/flutter_messenger.h',
      'out/host_debug/flutter_plugin_registrar.h',
      'out/host_debug/flutter_windows.dll',
      'out/host_debug/flutter_windows.dll.exp',
      'out/host_debug/flutter_windows.dll.lib',
      'out/host_debug/flutter_windows.dll.pdb',
    ], archive_name='windows-x64-flutter.zip')
    UploadFolder(api,
      'Upload windows-x64 Flutter library C++ wrapper',
      'src/out/host_debug',
      'cpp_client_wrapper',
      'flutter-cpp-client-wrapper.zip',
      'windows-x64')

    UploadDartSdk(api, archive_name='dart-sdk-windows-x64.zip')
    UploadWebSdk(api, archive_name='flutter-web-sdk-windows-x64.zip')

  if api.properties.get('build_android_aot', True):
    RunGN(api, '--runtime-mode', 'profile', '--android')
    RunGN(api, '--runtime-mode', 'profile', '--android', '--android-cpu=arm64')
    RunGN(api, '--runtime-mode', 'release', '--android')
    RunGN(api, '--runtime-mode', 'release', '--android', '--android-cpu=arm64')
    Build(api, 'android_profile', 'gen_snapshot')
    Build(api, 'android_profile_arm64', 'gen_snapshot')
    Build(api, 'android_release', 'gen_snapshot')
    Build(api, 'android_release_arm64', 'gen_snapshot')
    UploadArtifacts(api, "android-arm-profile" , [
      'out/android_profile/gen_snapshot.exe',
    ], archive_name='windows-x64.zip')
    UploadArtifacts(api, "android-arm64-profile" , [
      'out/android_profile_arm64/gen_snapshot.exe',
    ], archive_name='windows-x64.zip')
    UploadArtifacts(api, "android-arm-release" , [
      'out/android_release/gen_snapshot.exe',
    ], archive_name='windows-x64.zip')
    UploadArtifacts(api, "android-arm64-release" , [
      'out/android_release_arm64/gen_snapshot.exe',
    ], archive_name='windows-x64.zip')

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

@contextmanager
def InstallJazzy(api):
  gem_dir = api.path['start_dir'].join('gems')
  api.file.ensure_directory('mkdir gems', gem_dir)
  with api.context(cwd=gem_dir):
    api.step('install gems', [
        'gem', 'install', 'jazzy:' + api.properties['jazzy_version'],
        '--install-dir', '.'])
  with api.context(env={"GEM_HOME": gem_dir}, env_prefixes={
      'PATH': [gem_dir.join('bin')]}):
    yield

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
  soln.revision = api.buildbucket.gitiles_commit.id
  # TODO(eseidel): What does parent_got_revision_mapping do?  Do I care?
  src_cfg.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'
  src_cfg.target_os = set(['android'])
  src_cfg.repo_path_map[
    'https://chromium.googlesource.com/external/github.com/flutter/flutter'
  ] = ('src/flutter', 'HEAD')
  api.gclient.c = src_cfg
  api.gclient.c.got_revision_mapping['src/flutter'] = 'got_engine_revision'
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()

def RunSteps(api):
  GetCheckout(api)

  checkout = api.path['start_dir'].join('src')
  dart_bin = checkout.join(
      'third_party', 'dart', 'tools', 'sdks', 'dart-sdk', 'bin')

  api.goma.ensure_goma()

  env = {'GOMA_DIR': api.goma.goma_dir}
  env_prefixes = {'PATH': [dart_bin]}

  # The context adds dart to the path, only needed for the analyze step for now.
  with api.context(env=env, env_prefixes=env_prefixes):
    if api.platform.is_linux:
      AnalyzeDartUI(api)
      if api.properties.get('build_host', True):
        BuildLinux(api)
        TestObservatory(api)
      #TestEngine(api)
      BuildLinuxAndroid(api)
      VerifyExportedSymbols(api)
      BuildFuchsia(api)

    if api.platform.is_mac:
      with SetupXcode(api):
        BuildMac(api)
        if api.properties.get('build_ios', True):
          BuildIOS(api)
          with InstallJazzy(api):
            BuildObjcDoc(api)
        VerifyExportedSymbols(api)
        BuildFuchsia(api)

    if api.platform.is_win:
      BuildWindows(api)

# pylint: disable=line-too-long
# See https://chromium.googlesource.com/infra/luci/recipes-py/+/refs/heads/master/doc/user_guide.md
# The tests in here make sure that every line of code is used and does not fail.
# pylint: enable=line-too-long
def GenTests(api):
  for platform in ('mac', 'linux', 'win'):
    test = (
      api.test(platform) + api.platform(platform, 64) +
      api.buildbucket.ci_build(
        builder='%s Engine' % platform.capitalize(),
        git_repo=GIT_REPO,
        project='flutter',
      ) +
      api.properties(
        goma_jobs=1024,
        build_host=True,
        build_android_aot=True,
        build_android_debug=True,
        build_android_vulkan=True,
      )
    )
    if platform == 'mac':
      test += (api.properties(jazzy_version='0.8.4'))
    yield test

  yield (
    api.test('experimental') +
    api.buildbucket.ci_build(
        builder='Linux Engine',
        git_repo=GIT_REPO,
        project='flutter',
    ) +
    api.runtime(is_luci=True, is_experimental=True) +
    api.properties(goma_jobs=1024)
  )

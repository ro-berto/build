# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file is a copy of engine.py from
# 62f52b6e2a50f2df3ec81509f93c578847e03947, or the version of the recipe at
# the time v1.12.13's version of the engine was built.

from contextlib import contextmanager
import contextlib

from PB.recipes.build.flutter.engine import InputProperties
from PB.recipes.build.flutter.engine import EnvProperties

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from google.protobuf import struct_pb2

DEPS = [
    'build',
    'depot_tools/bot_update',
    'depot_tools/depot_tools',
    'depot_tools/gclient',
    'depot_tools/git',
    'depot_tools/gsutil',
    'depot_tools/osx_sdk',
    'goma',
    'recipe_engine/buildbucket',
    'recipe_engine/cipd',
    'recipe_engine/context',
    'recipe_engine/isolated',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/runtime',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'recipe_engine/python',
    'zip',
]

BUCKET_NAME = 'flutter_infra'
MAVEN_BUCKET_NAME = 'download.flutter.io'
ICU_DATA_PATH = 'third_party/icu/flutter/icudtl.dat'
GIT_REPO = (
    'https://chromium.googlesource.com/external/github.com/flutter/engine')

PROPERTIES = InputProperties
ENV_PROPERTIES = EnvProperties


def GetCheckoutPath(api):
  return api.path['cache'].join('builder', 'src')


def ShouldUploadPackages(api):
  return api.properties.get('upload_packages', False)


def GetCloudPath(api, path):
  git_hash = api.buildbucket.gitiles_commit.id
  if api.runtime.is_experimental:
    return 'flutter/experimental/%s/%s' % (git_hash, path)
  return 'flutter/%s/%s' % (git_hash, path)


def Build(api, config, *targets):
  checkout = GetCheckoutPath(api)
  build_dir = checkout.join('out/%s' % config)
  goma_jobs = api.properties['goma_jobs']
  ninja_args = [api.depot_tools.ninja_path, '-j', goma_jobs, '-C', build_dir]
  ninja_args.extend(targets)
  api.goma.build_with_goma(
      name='build %s' % ' '.join([config] + list(targets)),
      ninja_command=ninja_args)


# Bitcode builds cannot use goma.
def BuildNoGoma(api, config, *targets):
  if api.properties.get('no_bitcode', False):
    Build(api, config, *targets)
    return

  checkout = GetCheckoutPath(api)
  build_dir = checkout.join('out/%s' % config)
  ninja_args = [api.depot_tools.autoninja_path, '-C', build_dir]
  ninja_args.extend(targets)
  api.step('build %s' % ' '.join([config] + list(targets)), ninja_args)


def RunTests(api, out_dir, android_out_dir=None, types='all'):
  script_path = GetCheckoutPath(api).join('flutter', 'testing', 'run_tests.py')
  args = ['--variant', out_dir, '--type', types]
  if android_out_dir:
    args.extend(['--android-variant', android_out_dir])
  api.python('Host Tests for %s' % out_dir, script_path, args)


def ScheduleBuilds(api, builder_name, drone_props):
  req = api.buildbucket.schedule_request(
      swarming_parent_run_id=api.swarming.task_id,
      builder=builder_name,
      properties=drone_props)
  return api.buildbucket.schedule([req])


def CancelBuilds(api, builds):
  for build in builds:
    api.buildbucket.cancel_build(build.id)


def CollectBuilds(api, builds):
  return api.buildbucket.collect_builds([build.id for build in builds])


def GetFlutterFuchsiaBuildTargets(product, include_test_targets=False):
  targets = ['flutter/shell/platform/fuchsia:fuchsia']
  if include_test_targets:
    targets.append(
        'flutter/shell/platform/fuchsia/flutter:flutter_runner_tests')
  return targets


def GetFuchsiaOutputFiles(product):
  return [
      'dart_jit_%srunner' % ('product_' if product else ''),
      'dart_aot_%srunner' % ('product_' if product else ''),
      'flutter_jit_%srunner' % ('product_' if product else ''),
      'flutter_aot_%srunner' % ('product_' if product else ''),
  ]


def GetFuchsiaOutputDirs(product, build_mode, target_arch):
  return [
      'dart_jit_%srunner_far' % ('product_' if product else ''),
      'dart_aot_%srunner_far' % ('product_' if product else ''),
      'flutter_jit_%srunner_far' % ('product_' if product else ''),
      'flutter_aot_%srunner_far' % ('product_' if product else ''),
      'dart_runner_patched_sdk',
      'flutter_runner_patched_sdk',
      'clang_x64',
      'flutter-debug-symbols-%s-fuchsia-%s' % (build_mode, target_arch),
  ]


def BuildAndTestFuchsia(api, build_script, git_rev):
  RunGN(api, '--fuchsia', '--fuchsia-cpu', 'x64', '--runtime-mode', 'debug',
        '--no-lto')
  Build(api, 'fuchsia_debug_x64', *GetFlutterFuchsiaBuildTargets(False, True))

  fuchsia_package_cmd = [
      'python', build_script, '--engine-version', git_rev, '--skip-build',
      '--archs', 'x64', '--runtime-mode', 'debug'
  ]

  if api.platform.is_linux:
    api.step('Package Fuchsia Artifacts', fuchsia_package_cmd)
    TestFuchsia(api)

  RunGN(api, '--fuchsia', '--fuchsia-cpu', 'arm64', '--runtime-mode', 'debug',
        '--no-lto')
  Build(api, 'fuchsia_debug_arm64', *GetFlutterFuchsiaBuildTargets(False, True))


def RunGN(api, *args):
  checkout = GetCheckoutPath(api)
  gn_cmd = ['python', checkout.join('flutter/tools/gn'), '--goma']
  gn_cmd.extend(args)
  api.step('gn %s' % ' '.join(args), gn_cmd)


# Bitcode builds cannot use goma.
def RunGNBitcode(api, *args):
  if api.properties.get('no_bitcode', False):
    RunGN(api, *args)
    return

  # flutter/tools/gn assumes access to depot_tools on path for `ninja`.
  with api.depot_tools.on_path():
    checkout = GetCheckoutPath(api)
    gn_cmd = [
        'python',
        checkout.join('flutter/tools/gn'), '--bitcode', '--no-goma'
    ]
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
    pkg = api.zip.make_package(GetCheckoutPath(api), local_zip)
    AddFiles(api, pkg, file_paths)

    pkg.zip('Zip %s %s' % (platform, archive_name))
    if ShouldUploadPackages(api):
      api.gsutil.upload(
          local_zip, BUCKET_NAME, remote_zip, name='upload "%s"' % remote_name)


# Takes an artifact filename such as `flutter_embedding_release.jar`
# and returns `io/flutter/flutter_embedding_release/1.0.0-<hash>/
# flutter_embedding_release-1.0.0-<hash>.jar`.
def GetCloudMavenPath(api, artifact_filename, swarming_task_id):
  if api.runtime.is_experimental:
    # If this is not somewhat unique then led tasks will fail with
    # a missing delete permission.
    engine_git_hash = 'experimental-%s' % swarming_task_id
  else:
    engine_git_hash = api.buildbucket.gitiles_commit.id or 'testing'

  artifact_id, artifact_extension = artifact_filename.split('.', 2)

  # Source artifacts
  if artifact_id.endswith('-sources'):
    filename_pattern = '%s-1.0.0-%s-sources.%s'
  else:
    filename_pattern = '%s-1.0.0-%s.%s'

  artifact_id = artifact_id.replace('-sources', '')
  filename = filename_pattern % (artifact_id, engine_git_hash,
                                 artifact_extension)

  return 'io/flutter/%s/1.0.0-%s/%s' % (artifact_id, engine_git_hash, filename)


# Uploads the local Maven artifact.
def UploadMavenArtifacts(api, artifacts, swarming_task_id):
  if api.properties.get('no_maven', False):
    return
  if not ShouldUploadPackages(api):
    return
  checkout = GetCheckoutPath(api)

  for local_artifact in artifacts:
    filename = api.path.basename(local_artifact)
    remote_artifact = GetCloudMavenPath(api, filename, swarming_task_id)

    api.gsutil.upload(
        checkout.join(local_artifact),
        MAVEN_BUCKET_NAME,
        remote_artifact,
        name='upload "%s"' % remote_artifact)


def UploadFolder(api,
                 dir_label,
                 parent_dir,
                 folder_name,
                 zip_name,
                 platform=None):
  with MakeTempDir(api, dir_label) as temp_dir:
    local_zip = temp_dir.join(zip_name)
    if platform is None:
      remote_name = zip_name
    else:
      remote_name = '%s/%s' % (platform, zip_name)
    remote_zip = GetCloudPath(api, remote_name)
    parent_dir = api.path['cache'].join('builder', parent_dir)
    pkg = api.zip.make_package(parent_dir, local_zip)
    pkg.add_directory(parent_dir.join(folder_name))
    pkg.zip('Zip %s' % folder_name)
    if ShouldUploadPackages(api):
      api.gsutil.upload(
          local_zip, BUCKET_NAME, remote_zip, name='upload %s' % remote_name)


def UploadDartPackage(api, package_name):
  UploadFolder(
      api,
      'UploadDartPackage %s' % package_name,  # dir_label
      'src/out/android_debug/dist/packages',  # parent_dir
      package_name,  # folder_name
      "%s.zip" % package_name)  # zip_name


def UploadSkyEngineToCIPD(api, package_name):
  git_rev = api.buildbucket.gitiles_commit.id or 'HEAD'
  package_dir = 'src/out/android_debug/dist/packages'
  parent_dir = api.path['cache'].join('builder', package_dir)
  folder_path = parent_dir.join(package_name)
  with MakeTempDir(api, package_name) as temp_dir:
    zip_path = temp_dir.join('%s.zip' % package_name)
    cipd_package_name = 'flutter/%s' % package_name
    api.cipd.build(
        folder_path, zip_path, cipd_package_name, install_mode='copy')
    if ShouldUploadPackages(api):
      api.cipd.register(
          cipd_package_name,
          zip_path,
          refs=['latest'],
          tags={'git_revision': git_rev})


def UploadSkyEngineDartPackage(api):
  UploadDartPackage(api, 'sky_engine')
  UploadSkyEngineToCIPD(api, 'sky_engine')


def UploadFlutterPatchedSdk(api):
  UploadFolder(
      api,
      'Upload Flutter patched sdk',  # dir_label
      'src/out/host_debug',  # parent_dir
      'flutter_patched_sdk',  # folder_name
      'flutter_patched_sdk.zip')  # zip_name

  host_release_path = GetCheckoutPath(api).join('out/host_release')
  flutter_patched_sdk_product = host_release_path.join(
      'flutter_patched_sdk_product')
  api.file.rmtree('Remove stale flutter_patched_sdk_product',
                  flutter_patched_sdk_product)
  api.file.move(
      'Move release flutter_patched_sdk to flutter_patched_sdk_product',
      host_release_path.join('flutter_patched_sdk'),
      flutter_patched_sdk_product)
  UploadFolder(
      api,
      'Upload Product Flutter patched sdk',  # dir_label
      'src/out/host_release',  # parent_dir
      'flutter_patched_sdk_product',  # folder_name
      'flutter_patched_sdk_product.zip')  # zip_name


def UploadDartSdk(api, archive_name):
  UploadFolder(
      api,
      'Upload Dart SDK',  # dir_label
      'src/out/host_debug',  # parent_dir
      'dart-sdk',  # folder_name
      archive_name)


def UploadWebSdk(api, archive_name):
  UploadFolder(
      api,
      'Upload Web SDK',  # dir_label
      'src/out/host_debug',  # parent_dir
      'flutter_web_sdk',  # folder_name
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

  checkout = GetCheckoutPath(api)
  with api.context(cwd=checkout):
    api.step('analyze dart_ui', ['/bin/bash', 'flutter/ci/analyze.sh'])


def VerifyExportedSymbols(api):
  checkout = GetCheckoutPath(api)
  out_dir = checkout.join('out')
  script_dir = checkout.join('flutter/testing/symbols')
  script_path = script_dir.join('verify_exported.dart')
  with api.context(cwd=script_dir):
    api.step('pub get for verify_exported.dart', ['pub', 'get'])
  api.step('Verify exported symbols on release binaries',
           ['dart', script_path, out_dir])


def UploadTreeMap(api, upload_dir, lib_flutter_path, android_triple):
  with MakeTempDir(api, 'treemap') as temp_dir:
    checkout = GetCheckoutPath(api)
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
        "--addr2line-binary", addr2line
    ]

    api.python('generate treemap for %s' % upload_dir, script_path, args)

    remote_name = GetCloudPath(api, upload_dir)
    if ShouldUploadPackages(api):
      result = api.gsutil.upload(
          destionation_dir,
          BUCKET_NAME,
          remote_name,
          args=['-r'],
          name='upload treemap for %s' % lib_flutter_path,
          link_name=None)
      result.presentation.links['Open Treemap'] = (
          'https://storage.googleapis.com/%s/%s/sizes/index.html' %
          (BUCKET_NAME, remote_name))


def BuildLinuxAndroid(api, swarming_task_id):
  if api.properties.get('build_android_jit_release', True):
    jit_release_variants = [
        ('x86', 'android_jit_release_x86', 'android-x86-jit-release', True,
         'x86'),
    ]
    for android_cpu, out_dir, artifact_dir, \
            run_tests, abi in jit_release_variants:
      RunGN(api, '--android', '--android-cpu=%s' % android_cpu,
            '--runtime-mode=jit_release')
      Build(api, out_dir)
      if run_tests:
        RunTests(api, out_dir, android_out_dir=out_dir, types='java')
      artifacts = ['out/%s/flutter.jar' % out_dir]
      UploadArtifacts(api, artifact_dir, artifacts)

  if api.properties.get('build_android_debug', True):
    debug_variants = [
        ('arm', 'android_debug', 'android-arm', True, 'armeabi_v7a'),
        ('arm64', 'android_debug_arm64', 'android-arm64', False, 'arm64_v8a'),
        ('x86', 'android_debug_x86', 'android-x86', False, 'x86'),
        ('x64', 'android_debug_x64', 'android-x64', False, 'x86_64'),
    ]
    for android_cpu, out_dir, artifact_dir, run_tests, abi in debug_variants:
      RunGN(api, '--android', '--android-cpu=%s' % android_cpu, '--no-lto')
      Build(api, out_dir)
      if run_tests:
        RunTests(api, out_dir, android_out_dir=out_dir, types='java')
      artifacts = ['out/%s/flutter.jar' % out_dir]
      if android_cpu in ['x86', 'x64']:
        artifacts.append('out/%s/lib.stripped/libflutter.so' % out_dir)
      UploadArtifacts(api, artifact_dir, artifacts)
      UploadArtifacts(
          api,
          artifact_dir, ['out/%s/libflutter.so' % out_dir],
          archive_name='symbols.zip')

      # Upload the Maven artifacts.
      engine_filename = '%s_debug' % abi
      UploadMavenArtifacts(api, [
          'out/%s/%s.jar' % (out_dir, engine_filename),
          'out/%s/%s.pom' % (out_dir, engine_filename),
      ], swarming_task_id)

    # Upload the embedding
    UploadMavenArtifacts(api, [
        'out/android_debug/flutter_embedding_debug.jar',
        'out/android_debug/flutter_embedding_debug.pom',
        'out/android_debug/flutter_embedding_debug-sources.jar',
    ], swarming_task_id)

    Build(api, 'android_debug', ':dist')
    UploadSkyEngineDartPackage(api)
    BuildJavadoc(api)

  if api.properties.get('build_android_vulkan', True):
    RunGN(api, '--runtime-mode', 'release', '--android', '--enable-vulkan')
    Build(api, 'android_release_vulkan')

  if api.properties.get('build_android_aot', True):
    # This shard needs to build the Dart SDK to build the profile firebase app.
    RunGN(api, '--runtime-mode', 'profile', '--unoptimized', '--no-lto')
    Build(api, 'host_profile_unopt')

    # Build and upload engines for the runtime modes that use AOT compilation.
    # Do arm64 first because we have more tests for that one, and can bail out
    # earlier if they fail.
    aot_variants = [
        ('arm64', 'android_%s_arm64', 'android-arm64-%s', 'clang_x64',
         'aarch64-linux-android', 'arm64_v8a'),
        ('arm', 'android_%s', 'android-arm-%s', 'clang_x64',
         'arm-linux-androideabi', 'armeabi_v7a'),
        ('x64', 'android_%s_x64', 'android-x64-%s', 'clang_x64',
         'x86_64-linux-android', 'x86_64'),
    ]
    for (android_cpu, out_dir, artifact_dir, clang_dir, android_triple,
         abi) in aot_variants:
      for runtime_mode in ['profile', 'release']:
        build_output_dir = out_dir % runtime_mode
        upload_dir = artifact_dir % runtime_mode

        RunGN(api, '--android', '--runtime-mode=' + runtime_mode,
              '--android-cpu=%s' % android_cpu)
        Build(api, build_output_dir)
        Build(api, build_output_dir, "%s/gen_snapshot" % clang_dir)

        if runtime_mode == 'profile' and android_cpu == 'arm64':
          checkout = GetCheckoutPath(api)
          scenario_app_dir = checkout.join('flutter', 'testing', 'scenario_app')
          host_profile_dir = checkout.join('out', 'host_profile_unopt')
          gen_snapshot_dir = checkout.join('out', build_output_dir, 'clang_x64')
          with api.context(cwd=checkout):
            compile_cmd = [
                './flutter/testing/scenario_app/assemble_apk.sh',
                host_profile_dir, gen_snapshot_dir
            ]
            api.step('Build scenario app', compile_cmd)
            firebase_cmd = [
                './flutter/ci/firebase_testlab.sh',
                scenario_app_dir.join('android', 'app', 'build', 'outputs',
                                      'apk', 'debug', 'app-debug.apk'),
                api.buildbucket.gitiles_commit.id or 'testing',
                swarming_task_id,
            ]
            api.step('Firebase test', firebase_cmd, ok_ret='any')

        # TODO(egarciad): Don't upload flutter.jar once the migration to Maven
        # is completed.
        UploadArtifacts(api, upload_dir, [
            'out/%s/flutter.jar' % build_output_dir,
        ])

        # Upload the Maven artifacts.
        UploadMavenArtifacts(api, [
            'out/%s/%s_%s.jar' % (build_output_dir, abi, runtime_mode),
            'out/%s/%s_%s.pom' % (build_output_dir, abi, runtime_mode),
        ], swarming_task_id)

        # Upload artifacts used for AOT compilation on Linux hosts.
        UploadArtifacts(
            api,
            upload_dir, [
                'out/%s/%s/gen_snapshot' % (build_output_dir, clang_dir),
            ],
            archive_name='linux-x64.zip')
        unstripped_lib_flutter_path = 'out/%s/libflutter.so' % build_output_dir
        UploadArtifacts(
            api,
            upload_dir, [unstripped_lib_flutter_path],
            archive_name='symbols.zip')

        if runtime_mode == 'release' and android_cpu != 'x64':
          UploadTreeMap(api, upload_dir, unstripped_lib_flutter_path,
                        android_triple)

    # Upload the embedding
    for runtime_mode in ['profile', 'release']:
      build_output_dir = out_dir % runtime_mode
      UploadMavenArtifacts(api, [
          'out/%s/flutter_embedding_%s.jar' % (build_output_dir, runtime_mode),
          'out/%s/flutter_embedding_%s.pom' % (build_output_dir, runtime_mode),
          'out/%s/flutter_embedding_%s-sources.jar' %
          (build_output_dir, runtime_mode),
      ], swarming_task_id)


def BuildLinux(api):
  RunGN(api, '--runtime-mode', 'debug', '--full-dart-sdk')
  RunGN(api, '--runtime-mode', 'debug', '--unoptimized')
  RunGN(api, '--runtime-mode', 'release')
  Build(api, 'host_debug_unopt')
  RunTests(api, 'host_debug_unopt', types='dart,engine')
  Build(api, 'host_debug')
  Build(api, 'host_release')
  UploadArtifacts(api, 'linux-x64', [
      ICU_DATA_PATH,
      'out/host_debug/flutter_tester',
      'out/host_debug_unopt/gen/flutter/lib/snapshot/isolate_snapshot.bin',
      'out/host_debug_unopt/gen/flutter/lib/snapshot/vm_isolate_snapshot.bin',
      'out/host_debug_unopt/gen/frontend_server.dart.snapshot',
  ])
  UploadArtifacts(
      api,
      'linux-x64', [
          'out/host_debug/flutter_embedder.h',
          'out/host_debug/libflutter_engine.so',
      ],
      archive_name='linux-x64-embedder')

  UploadArtifacts(
      api,
      'linux-x64', [
          'out/host_debug/flutter_export.h',
          'out/host_debug/flutter_glfw.h',
          'out/host_debug/flutter_messenger.h',
          'out/host_debug/flutter_plugin_registrar.h',
          'out/host_debug/libflutter_linux_glfw.so',
      ],
      archive_name='linux-x64-flutter-glfw.zip')
  UploadFolder(api, 'Upload linux-x64 Flutter GLFW library C++ wrapper',
               'src/out/host_debug', 'cpp_client_wrapper_glfw',
               'flutter-cpp-client-wrapper-glfw.zip', 'linux-x64')

  UploadFlutterPatchedSdk(api)
  UploadDartSdk(api, archive_name='dart-sdk-linux-x64.zip')
  UploadWebSdk(api, archive_name='flutter-web-sdk-linux-x64.zip')


def GetFuchsiaBuildId(api):
  checkout = GetCheckoutPath(api)
  manifest_path = checkout.join('fuchsia', 'sdk', 'linux', 'meta',
                                'manifest.json')
  manifest_data = api.file.read_json(
      'Read manifest', manifest_path, test_data={'id': 123})
  return manifest_data['id']


def DownloadFuchsiaSystemImage(api, target_dir, bucket_name, build_id,
                               image_name):
  api.gsutil.download(bucket_name,
                      'development/%s/images/%s' % (build_id, image_name),
                      target_dir)


def PackageFlutterRunnerTests(api, checkout, fuchsia_tools):
  package_cmd = [
      checkout.join('flutter', 'tools', 'fuchsia', 'gen_package.py'),
      '--pm-bin',
      fuchsia_tools.join('pm'),
      '--package-dir',
      checkout.join('out', 'fuchsia_debug_x64', 'flutter_runner_tests_far'),
      '--signing-key',
      checkout.join('flutter', 'tools', 'fuchsia', 'development.key'),
      '--far-name',
      'flutter_runner_tests',
  ]
  api.step('Generate far', package_cmd)


def IsolateFuchsiaTestArtifacts(api, checkout, fuchsia_tools, image_name):
  """
  Gets the system image for the current Fuchsia SDK from cloud storage, adds it
  to an isolated along with the `pm` and `dev_finder` utilities, as well as the
  flutter_runner_tests and the flutter_runner FAR, and a bash script (in
  engine.resources/fuchsia-tests.sh) to drive the flutter_ctl.
  """
  with MakeTempDir(api, 'isolated') as isolated_dir:
    with api.step.nest('Copy files'):
      api.file.copy('Copy test script', api.resource('fuchsia-tests.sh'),
                    isolated_dir)
      api.file.copy('Copy dev_finder', fuchsia_tools.join('dev_finder'),
                    isolated_dir)
      api.file.copy('Copy pm', fuchsia_tools.join('pm'), isolated_dir)
      api.file.copy(
          'Copy flutter_runner far',
          checkout.join('out', 'fuchsia_bucket', 'flutter', 'x64', 'debug',
                        'aot', 'flutter_aot_runner-0.far'), isolated_dir)
      api.file.copy(
          'Copy flutter_runner_tests far',
          checkout.join('out', 'fuchsia_debug_x64',
                        'flutter_runner_tests-0.far'), isolated_dir)

    DownloadFuchsiaSystemImage(api, isolated_dir, 'fuchsia',
                               GetFuchsiaBuildId(api), image_name)
    isolated = api.isolated.isolated(isolated_dir)
    isolated.add_dir(isolated_dir)
    return isolated.archive('Archive Fuchsia Test Isolate')


def TestFuchsia(api):
  """
  Packages the flutter_runner build artifacts into a FAR, and then sends them
  and related artifacts to isolated. The isolated is used to create a swarming
  task that:
    - Downloads the isolated artifacts
    - Gets fuchsia_ctl from CIPD
    - Runs the script to pave, test, and reboot the Fuchsia device
  """
  checkout = GetCheckoutPath(api)
  fuchsia_tools = checkout.join('fuchsia', 'sdk', 'linux', 'tools')
  image_name = 'generic-x64.tgz'

  PackageFlutterRunnerTests(api, checkout, fuchsia_tools)
  isolated_hash = IsolateFuchsiaTestArtifacts(api, checkout, fuchsia_tools,
                                              image_name)

  ensure_file = api.cipd.EnsureFile()
  ensure_file.add_package('flutter/fuchsia_ctl/${platform}',
                          api.properties.get('fuchsia_ctl_version'))

  request = (
      api.swarming.task_request().with_name('flutter_runner_fuchsia')
      .with_priority(100))

  request = (
      request.with_slice(
          0, request[0].with_cipd_ensure_file(ensure_file).with_command(
              ['./fuchsia-tests.sh',
               image_name]).with_dimensions(pool='luci.flutter.tests')
          .with_isolated(isolated_hash).with_expiration_secs(
              3600).with_io_timeout_secs(3600).with_execution_timeout_secs(
                  3600).with_idempotent(True).with_containment_type('AUTO')))

  # Trigger the task request.
  metadata = api.swarming.trigger('Trigger Fuchsia Tests', requests=[request])
  # Collect the result of the task by metadata.
  fuchsia_output = api.path['cleanup'].join('fuchsia_test_output')
  api.file.ensure_directory('swarming output', fuchsia_output)
  results = api.swarming.collect(
      'collect', metadata, output_dir=fuchsia_output, timeout='30m')
  for result in results:
    result.analyze()


def UploadFuchsiaDebugSymbols(api):
  checkout = GetCheckoutPath(api)
  dbg_symbols_script = str(
      checkout.join('flutter/tools/fuchsia/merge_and_upload_debug_symbols.py'))
  git_rev = api.buildbucket.gitiles_commit.id or 'HEAD'

  archs = ['arm64', 'x64']
  modes = ['debug', 'profile', 'release']
  for arch in archs:
    symbol_dirs = []
    for mode in modes:
      base_dir = 'fuchsia_%s_%s' % (mode, arch)
      symbols_basename = 'flutter-debug-symbols-%s-fuchsia-%s' % (mode, arch)
      symbol_dir = checkout.join('out', base_dir, symbols_basename)
      symbol_dirs.append(symbol_dir)
    with MakeTempDir(api, 'FuchsiaDebugSymbols') as temp_dir:
      debug_symbols_cmd = [
          'python', dbg_symbols_script, '--engine-version', git_rev, '--upload',
          '--target-arch', arch, '--out-dir', temp_dir, '--symbol-dirs'
      ] + symbol_dirs
      api.step('Upload Fuchsia Debug Symbols for %s' % arch, debug_symbols_cmd)
  return


def BuildFuchsia(api):
  """
  This schedules release and profile builds for x64 and arm64 on other bots,
  and then builds the x64 and arm64 runners (which do not require LTO and thus
  are faster to build). On Linux, we also run tests for the runner against x64,
  and if they fail we cancel the scheduled builds.
  """
  fuchsia_build_pairs = [
      ('arm64', 'profile'),
      ('arm64', 'release'),
      ('x64', 'profile'),
      ('x64', 'release'),
  ]
  builds = []
  for arch, build_mode in fuchsia_build_pairs:
    gn_args = ['--fuchsia', '--fuchsia-cpu', arch, '--runtime-mode', build_mode]
    product = build_mode == 'release'
    fuchsia_output_dirs = GetFuchsiaOutputDirs(product, build_mode, arch)
    builds += ScheduleBuilds(
        api, 'Linux Engine Drone', {
            'builds': [{
                'gn_args': gn_args,
                'dir': 'fuchsia_%s_%s' % (build_mode, arch),
                'targets': GetFlutterFuchsiaBuildTargets(product),
                'output_files': GetFuchsiaOutputFiles(product),
                'output_dirs': fuchsia_output_dirs,
            }]
        })

  checkout = GetCheckoutPath(api)
  build_script = str(
      checkout.join('flutter/tools/fuchsia/build_fuchsia_artifacts.py'))
  git_rev = api.buildbucket.gitiles_commit.id or 'HEAD'

  try:
    BuildAndTestFuchsia(api, build_script, git_rev)
  except (api.step.StepFailure, api.step.InfraFailure) as e:
    CancelBuilds(api, builds)
    raise e

  builds = CollectBuilds(api, builds)
  for build_id in builds:
    api.isolated.download(
        'Download for build %s' % build_id,
        builds[build_id].output.properties['isolated_output_hash'],
        GetCheckoutPath(api))

  if ShouldUploadPackages(api) and not api.runtime.is_experimental:
    fuchsia_package_cmd = [
        'python',
        build_script,
        '--engine-version',
        git_rev,
        '--skip-build',
        '--upload',
    ]
    api.step('Upload Fuchsia Artifacts', fuchsia_package_cmd)
    UploadFuchsiaDebugSymbols(api)
    stamp_file = api.path['cleanup'].join('fuchsia_stamp')
    api.file.write_text('fuchsia.stamp', stamp_file, '')
    remote_file = GetCloudPath(api, 'fuchsia/fuchsia.stamp')
    api.gsutil.upload(
        stamp_file, BUCKET_NAME, remote_file, name='upload "fuchsia.stamp"')


def TestObservatory(api):
  checkout = GetCheckoutPath(api)
  flutter_tester_path = checkout.join('out/host_debug/flutter_tester')
  empty_main_path = \
      checkout.join('flutter/shell/testing/observatory/empty_main.dart')
  test_path = checkout.join('flutter/shell/testing/observatory/test.dart')
  test_cmd = ['dart', test_path, flutter_tester_path, empty_main_path]
  with api.context(cwd=checkout):
    api.step('test observatory and service protocol', test_cmd)


@contextmanager
def SetupXcode(api):
  # See cr-buildbucket.cfg for how the version is passed in.
  # https://github.com/flutter/infra/blob/master/config/cr-buildbucket.cfg#L148
  with api.osx_sdk('ios'):
    yield


def BuildMac(api):
  if api.properties.get('build_host', True):
    RunGN(api, '--runtime-mode', 'debug', '--no-lto', '--full-dart-sdk')
    RunGN(api, '--runtime-mode', 'debug', '--unoptimized', '--no-lto')
    RunGN(api, '--runtime-mode', 'profile', '--no-lto')
    RunGN(api, '--runtime-mode', 'release', '--no-lto')

    Build(api, 'host_debug_unopt')
    RunTests(api, 'host_debug_unopt', types='dart,engine')
    Build(api, 'host_debug')
    Build(api, 'host_profile')
    Build(api, 'host_release')
    host_debug_path = GetCheckoutPath(api).join('out', 'host_debug')
    host_profile_path = GetCheckoutPath(api).join('out', 'host_profile')
    host_release_path = GetCheckoutPath(api).join('out', 'host_release')

    api.zip.directory('Archive FlutterEmbedder.framework',
                      host_debug_path.join('FlutterEmbedder.framework'),
                      host_debug_path.join('FlutterEmbedder.framework.zip'))

    api.zip.directory('Archive FlutterMacOS.framework',
                      host_debug_path.join('FlutterMacOS.framework'),
                      host_debug_path.join('FlutterMacOS.framework.zip'))
    api.zip.directory('Archive FlutterMacOS.framework profile',
                      host_profile_path.join('FlutterMacOS.framework'),
                      host_profile_path.join('FlutterMacOS.framework.zip'))
    api.zip.directory('Archive FlutterMacOS.framework release',
                      host_release_path.join('FlutterMacOS.framework'),
                      host_release_path.join('FlutterMacOS.framework.zip'))

    UploadArtifacts(api, 'darwin-x64', [
        ICU_DATA_PATH,
        'out/host_debug/flutter_tester',
        'out/host_debug_unopt/gen/flutter/lib/snapshot/isolate_snapshot.bin',
        'out/host_debug_unopt/gen/flutter/lib/snapshot/vm_isolate_snapshot.bin',
        'out/host_debug_unopt/gen/frontend_server.dart.snapshot',
        'out/host_debug_unopt/gen_snapshot',
    ])
    UploadArtifacts(api, 'darwin-x64-profile', [
        'out/host_profile/gen_snapshot',
    ])
    UploadArtifacts(api, 'darwin-x64-release', [
        'out/host_release/gen_snapshot',
    ])

    UploadArtifacts(
        api,
        'darwin-x64', ['out/host_debug/FlutterEmbedder.framework.zip'],
        archive_name='FlutterEmbedder.framework.zip')

    flutter_podspec = \
        'flutter/shell/platform/darwin/macos/framework/FlutterMacOS.podspec'
    UploadArtifacts(
        api,
        'darwin-x64', [
            'out/host_debug/FlutterMacOS.framework.zip',
            flutter_podspec,
        ],
        archive_name='FlutterMacOS.framework.zip')
    UploadArtifacts(
        api,
        'darwin-x64-profile', [
            'out/host_profile/FlutterMacOS.framework.zip',
            flutter_podspec,
        ],
        archive_name='FlutterMacOS.framework.zip')
    UploadArtifacts(
        api,
        'darwin-x64-release', [
            'out/host_release/FlutterMacOS.framework.zip',
            flutter_podspec,
        ],
        archive_name='FlutterMacOS.framework.zip')

    UploadDartSdk(api, archive_name='dart-sdk-darwin-x64.zip')
    UploadWebSdk(api, archive_name='flutter-web-sdk-darwin-x64.zip')

  if api.properties.get('build_android_vulkan', True):
    RunGN(api, '--runtime-mode', 'release', '--android', '--enable-vulkan')
    Build(api, 'android_release_vulkan')

  if api.properties.get('build_android_aot', True):
    RunGN(api, '--runtime-mode', 'profile', '--android')
    RunGN(api, '--runtime-mode', 'profile', '--android', '--android-cpu=arm64')
    RunGN(api, '--runtime-mode', 'profile', '--android', '--android-cpu=x64')
    RunGN(api, '--runtime-mode', 'release', '--android')
    RunGN(api, '--runtime-mode', 'release', '--android', '--android-cpu=arm64')
    RunGN(api, '--runtime-mode', 'release', '--android', '--android-cpu=x64')

    Build(api, 'android_profile', 'flutter/lib/snapshot')
    Build(api, 'android_profile_arm64', 'flutter/lib/snapshot')
    Build(api, 'android_profile_x64', 'flutter/lib/snapshot')
    Build(api, 'android_release', 'flutter/lib/snapshot')
    Build(api, 'android_release_arm64', 'flutter/lib/snapshot')
    Build(api, 'android_release_x64', 'flutter/lib/snapshot')

    UploadArtifacts(
        api,
        "android-arm-profile", [
            'out/android_profile/clang_x64/gen_snapshot',
        ],
        archive_name='darwin-x64.zip')
    UploadArtifacts(
        api,
        "android-arm64-profile", [
            'out/android_profile_arm64/clang_x64/gen_snapshot',
        ],
        archive_name='darwin-x64.zip')
    UploadArtifacts(
        api,
        "android-x64-profile", [
            'out/android_profile_x64/clang_x64/gen_snapshot',
        ],
        archive_name='darwin-x64.zip')
    UploadArtifacts(
        api,
        "android-arm-release", [
            'out/android_release/clang_x64/gen_snapshot',
        ],
        archive_name='darwin-x64.zip')
    UploadArtifacts(
        api,
        "android-arm64-release", [
            'out/android_release_arm64/clang_x64/gen_snapshot',
        ],
        archive_name='darwin-x64.zip')
    UploadArtifacts(
        api,
        "android-x64-release", [
            'out/android_release_x64/clang_x64/gen_snapshot',
        ],
        archive_name='darwin-x64.zip')


def PackageIOSVariant(api,
                      label,
                      arm64_out,
                      armv7_out,
                      sim_out,
                      bucket_name,
                      strip_bitcode=False):
  checkout = GetCheckoutPath(api)
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

  if strip_bitcode:
    create_ios_framework_cmd.append('--strip-bitcode')

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
      checkout.join('flutter/sky/tools/create_macos_gen_snapshots.py'),
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
      'out/%s/gen_snapshot_armv7' % label,
      'out/%s/gen_snapshot_arm64' % label,
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
    if ShouldUploadPackages(api):
      api.gsutil.upload(
          dsym_zip, BUCKET_NAME, remote_zip, name='upload "%s"' % remote_name)


def RunIOSTests(api):
  test_dir = GetCheckoutPath(api).join('flutter', 'testing')
  ios_unit_tests = test_dir.join('ios', 'IosUnitTests')
  scenario_app_tests = test_dir.join('scenario_app')

  with api.context(cwd=ios_unit_tests):
    api.step('iOS Unit Tests', ['./run_tests.sh', 'ios_debug_sim'])

  with api.context(cwd=scenario_app_tests):
    api.step('Scenario App Unit Tests', ['./run_ios_tests.sh', 'ios_debug_sim'])


def BuildIOS(api):
  # Simulator doesn't use bitcode.
  # Simulator binary is needed in all runtime modes.
  RunGN(api, '--ios', '--runtime-mode', 'debug', '--simulator', '--no-lto')
  Build(api, 'ios_debug_sim')

  if api.properties.get('ios_debug', True):
    # We need to build host_debug_unopt for testing
    RunGN(api, '--unoptimized')
    Build(api, 'host_debug_unopt')

    RunGN(api, '--ios', '--runtime-mode', 'debug', '--unoptimized',
          '--enable-metal')
    RunGNBitcode(api, '--ios', '--runtime-mode', 'debug')
    RunGNBitcode(api, '--ios', '--runtime-mode', 'debug', '--ios-cpu=arm')

    RunIOSTests(api)
    Build(api, 'ios_debug_unopt_metal')
    BuildNoGoma(api, 'ios_debug')
    BuildNoGoma(api, 'ios_debug_arm')
    BuildObjcDoc(api)

    PackageIOSVariant(api, 'debug', 'ios_debug', 'ios_debug_arm',
                      'ios_debug_sim', 'ios')

  if api.properties.get('ios_profile', True):
    RunGNBitcode(api, '--ios', '--runtime-mode', 'profile')
    RunGNBitcode(api, '--ios', '--runtime-mode', 'profile', '--ios-cpu=arm')
    BuildNoGoma(api, 'ios_profile')
    BuildNoGoma(api, 'ios_profile_arm')
    PackageIOSVariant(api, 'profile', 'ios_profile', 'ios_profile_arm',
                      'ios_debug_sim', 'ios-profile')

  if api.properties.get('ios_release', True):
    RunGNBitcode(api, '--ios', '--runtime-mode', 'release')
    RunGNBitcode(api, '--ios', '--runtime-mode', 'release', '--ios-cpu=arm')
    BuildNoGoma(api, 'ios_release')
    BuildNoGoma(api, 'ios_release_arm')
    PackageIOSVariant(api, 'release', 'ios_release', 'ios_release_arm',
                      'ios_debug_sim', 'ios-release')

    if not api.properties.get('no_bitcode', False):
      # Create a bitcode-stripped version. This will help customers who do not
      # need bitcode, which significantly increases download size. This should
      # be removed when bitcode is enabled by default in Flutter.
      PackageIOSVariant(api, 'release', 'ios_release', 'ios_release_arm',
                        'ios_debug_sim', 'ios-release-nobitcode', True)


def BuildWindows(api):
  if api.properties.get('build_host', True):
    RunGN(api, '--runtime-mode', 'debug', '--full-dart-sdk', '--no-lto')
    Build(api, 'host_debug')
    RunTests(api, 'host_debug', types='engine')
    UploadArtifacts(api, 'windows-x64', [
        ICU_DATA_PATH,
        'out/host_debug/flutter_tester.exe',
        'out/host_debug/gen/flutter/lib/snapshot/isolate_snapshot.bin',
        'out/host_debug/gen/flutter/lib/snapshot/vm_isolate_snapshot.bin',
        'out/host_debug/gen/frontend_server.dart.snapshot',
    ])

    UploadArtifacts(
        api,
        'windows-x64', [
            'out/host_debug/flutter_embedder.h',
            'out/host_debug/flutter_engine.dll',
            'out/host_debug/flutter_engine.dll.exp',
            'out/host_debug/flutter_engine.dll.lib',
            'out/host_debug/flutter_engine.dll.pdb',
        ],
        archive_name='windows-x64-embedder.zip')

    UploadArtifacts(
        api,
        'windows-x64', [
            'out/host_debug/flutter_export.h',
            'out/host_debug/flutter_windows.h',
            'out/host_debug/flutter_messenger.h',
            'out/host_debug/flutter_plugin_registrar.h',
            'out/host_debug/flutter_windows.dll',
            'out/host_debug/flutter_windows.dll.exp',
            'out/host_debug/flutter_windows.dll.lib',
            'out/host_debug/flutter_windows.dll.pdb',
        ],
        archive_name='windows-x64-flutter.zip')
    UploadFolder(api, 'Upload windows-x64 Flutter library C++ wrapper',
                 'src/out/host_debug', 'cpp_client_wrapper',
                 'flutter-cpp-client-wrapper.zip', 'windows-x64')

    # TODO: Remove this once the switch to the non-GLFW version above is
    # complete. See https://github.com/flutter/flutter/issues/38590.
    UploadArtifacts(
        api,
        'windows-x64', [
            'out/host_debug/flutter_export.h',
            'out/host_debug/flutter_glfw.h',
            'out/host_debug/flutter_messenger.h',
            'out/host_debug/flutter_plugin_registrar.h',
            'out/host_debug/flutter_windows_glfw.dll',
            'out/host_debug/flutter_windows_glfw.dll.exp',
            'out/host_debug/flutter_windows_glfw.dll.lib',
            'out/host_debug/flutter_windows_glfw.dll.pdb',
        ],
        archive_name='windows-x64-flutter-glfw.zip')
    UploadFolder(api, 'Upload windows-x64 Flutter GLFW library C++ wrapper',
                 'src/out/host_debug', 'cpp_client_wrapper_glfw',
                 'flutter-cpp-client-wrapper-glfw.zip', 'windows-x64')

    UploadDartSdk(api, archive_name='dart-sdk-windows-x64.zip')
    UploadWebSdk(api, archive_name='flutter-web-sdk-windows-x64.zip')

  if api.properties.get('build_android_aot', True):
    RunGN(api, '--runtime-mode', 'profile', '--android')
    RunGN(api, '--runtime-mode', 'profile', '--android', '--android-cpu=arm64')
    RunGN(api, '--runtime-mode', 'profile', '--android', '--android-cpu=x64')
    RunGN(api, '--runtime-mode', 'release', '--android')
    RunGN(api, '--runtime-mode', 'release', '--android', '--android-cpu=arm64')
    RunGN(api, '--runtime-mode', 'release', '--android', '--android-cpu=x64')
    Build(api, 'android_profile', 'gen_snapshot')
    Build(api, 'android_profile_arm64', 'gen_snapshot')
    Build(api, 'android_profile_x64', 'gen_snapshot')
    Build(api, 'android_release', 'gen_snapshot')
    Build(api, 'android_release_arm64', 'gen_snapshot')
    Build(api, 'android_release_x64', 'gen_snapshot')
    UploadArtifacts(
        api,
        "android-arm-profile", [
            'out/android_profile/gen_snapshot.exe',
        ],
        archive_name='windows-x64.zip')
    UploadArtifacts(
        api,
        "android-arm64-profile", [
            'out/android_profile_arm64/gen_snapshot.exe',
        ],
        archive_name='windows-x64.zip')
    UploadArtifacts(
        api,
        "android-x64-profile", [
            'out/android_profile_x64/gen_snapshot.exe',
        ],
        archive_name='windows-x64.zip')
    UploadArtifacts(
        api,
        "android-arm-release", [
            'out/android_release/gen_snapshot.exe',
        ],
        archive_name='windows-x64.zip')
    UploadArtifacts(
        api,
        "android-arm64-release", [
            'out/android_release_arm64/gen_snapshot.exe',
        ],
        archive_name='windows-x64.zip')
    UploadArtifacts(
        api,
        "android-x64-release", ['out/android_release_x64/gen_snapshot.exe'],
        archive_name='windows-x64.zip')


def BuildJavadoc(api):
  checkout = GetCheckoutPath(api)
  with MakeTempDir(api, 'BuildJavadoc') as temp_dir:
    javadoc_cmd = [
        checkout.join('flutter/tools/gen_javadoc.py'), '--out-dir', temp_dir
    ]
    with api.context(cwd=checkout):
      api.step('build javadoc', javadoc_cmd)
    api.zip.directory('archive javadoc', temp_dir,
                      checkout.join('out/android_javadoc.zip'))
  if ShouldUploadPackages(api):
    api.gsutil.upload(
        checkout.join('out/android_javadoc.zip'),
        BUCKET_NAME,
        GetCloudPath(api, 'android-javadoc.zip'),
        name='upload javadoc')


@contextmanager
def InstallGems(api):
  gem_dir = api.path['start_dir'].join('gems')
  api.file.ensure_directory('mkdir gems', gem_dir)
  with api.context(cwd=gem_dir):
    api.step('install jazzy', [
        'gem', 'install', 'jazzy:' + api.properties['jazzy_version'],
        '--install-dir', '.'
    ])
    api.step('install xcpretty', [
        'gem', 'install',
        'xcpretty:' + api.properties.get('xcpretty_version', '0.3.0'),
        '--install-dir', '.'
    ])
  with api.context(
      env={"GEM_HOME": gem_dir}, env_prefixes={'PATH': [gem_dir.join('bin')]}):
    yield


def BuildObjcDoc(api):
  """Builds documentation for the Objective-C variant of engine."""
  checkout = GetCheckoutPath(api)
  with MakeTempDir(api, 'BuildObjcDoc') as temp_dir:
    objcdoc_cmd = [checkout.join('flutter/tools/gen_objcdoc.sh'), temp_dir]
    with api.context(cwd=checkout.join('flutter')):
      api.step('build obj-c doc', objcdoc_cmd)
    api.zip.directory('archive obj-c doc', temp_dir,
                      checkout.join('out/ios-objcdoc.zip'))

    if ShouldUploadPackages(api):
      api.gsutil.upload(
          checkout.join('out/ios-objcdoc.zip'),
          BUCKET_NAME,
          GetCloudPath(api, 'ios-objcdoc.zip'),
          name='upload obj-c doc')


def GetCheckout(api):
  git_url = GIT_REPO
  git_id = api.buildbucket.gitiles_commit.id
  git_ref = api.buildbucket.gitiles_commit.ref
  if 'git_url' in api.properties and 'git_ref' in api.properties:
    git_url = api.properties['git_url']
    git_id = api.properties['git_ref']
    git_ref = api.properties['git_ref']

  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = 'src/flutter'
  soln.url = git_url
  soln.revision = git_id
  src_cfg.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'
  src_cfg.repo_path_map[git_url] = ('src/flutter', git_ref)
  api.gclient.c = src_cfg
  api.gclient.c.got_revision_mapping['src/flutter'] = 'got_engine_revision'
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()


def RunSteps(api, properties, env_properties):
  cache_root = api.path['cache'].join('builder')
  checkout = GetCheckoutPath(api)

  if properties.clobber:
    api.file.rmtree('Clobber cache', cache_root)

  api.file.rmtree('Clobber build output', checkout.join('out'))

  api.file.ensure_directory('Ensure checkout cache', cache_root)
  api.goma.ensure_goma()
  dart_bin = checkout.join('third_party', 'dart', 'tools', 'sdks', 'dart-sdk',
                           'bin')

  android_home = checkout.join('third_party', 'android_tools', 'sdk')

  env = {'GOMA_DIR': api.goma.goma_dir, 'ANDROID_HOME': str(android_home)}
  env_prefixes = {'PATH': [dart_bin]}

  # Various scripts we run assume access to depot_tools on path for `ninja`.
  with api.context(
      cwd=cache_root, env=env,
      env_prefixes=env_prefixes), api.depot_tools.on_path():
    GetCheckout(api)

    # Presence of tags in git repo is critical for determining dart version.
    dart_sdk_dir = GetCheckoutPath(api).join('third_party', 'dart')
    with api.context(cwd=dart_sdk_dir):
      api.step('Fetch dart tags', ['git', 'fetch'])
    api.gclient.runhooks()

    with api.step.nest('Android SDK Licenses'):
      api.file.ensure_directory('mkdir licenses', android_home.join('licenses'))
      api.file.write_text('android sdk license',
                          android_home.join('licenses', 'android-sdk-license'),
                          str(properties.android_sdk_license))
      api.file.write_text(
          'android sdk preview license',
          android_home.join('licenses', 'android-sdk-preview-license'),
          str(properties.android_sdk_preview_license))

    if api.platform.is_linux:
      if api.properties.get('build_host', True):
        AnalyzeDartUI(api)
        BuildLinux(api)
        TestObservatory(api)
      BuildLinuxAndroid(api, env_properties.SWARMING_TASK_ID)
      if api.properties.get('build_fuchsia', True):
        BuildFuchsia(api)
      VerifyExportedSymbols(api)

    if api.platform.is_mac:
      with SetupXcode(api):
        BuildMac(api)
        if api.properties.get('build_ios', True):
          with InstallGems(api):
            BuildIOS(api)
        if api.properties.get('build_fuchsia', True):
          BuildFuchsia(api)
        VerifyExportedSymbols(api)

    if api.platform.is_win:
      BuildWindows(api)


# pylint: disable=line-too-long
# See https://chromium.googlesource.com/infra/luci/recipes-py/+/refs/heads/master/doc/user_guide.md
# The tests in here make sure that every line of code is used and does not fail.
# pylint: enable=line-too-long
def GenTests(api):
  output_props = struct_pb2.Struct()
  output_props['isolated_output_hash'] = 'deadbeef'
  build = api.buildbucket.try_build_message(
      builder='Linux Drone', project='flutter')
  build.output.CopyFrom(build_pb2.Build.Output(properties=output_props))

  collect_build_output = api.buildbucket.simulated_collect_output([build])
  for platform in ('mac', 'linux', 'win'):
    for should_upload in (True, False):
      for maven_or_bitcode in (True, False):
        test = api.test(
            '%s%s%s' % (platform, '_upload' if should_upload else '',
                        '_maven_or_bitcode' if maven_or_bitcode else ''),
            api.platform(platform, 64),
            api.buildbucket.ci_build(
                builder='%s Engine' % platform.capitalize(),
                git_repo=GIT_REPO,
                project='flutter',
            ),
            api.properties(
                InputProperties(
                    clobber=False,
                    goma_jobs='1024',
                    fuchsia_ctl_version='version:0.0.2',
                    build_host=True,
                    build_fuchsia=True,
                    build_android_aot=True,
                    build_android_debug=True,
                    build_android_vulkan=True,
                    no_maven=maven_or_bitcode,
                    upload_packages=should_upload,
                    android_sdk_license='android_sdk_hash',
                    android_sdk_preview_license='android_sdk_preview_hash',
                ),),
            api.properties.environ(EnvProperties(SWARMING_TASK_ID='deadbeef')),
        )
        if platform != 'win':
          test += collect_build_output
        if platform == 'mac':
          test += (
              api.properties(
                  InputProperties(
                      jazzy_version='0.8.4',
                      build_ios=True,
                      no_bitcode=maven_or_bitcode)))
        yield test

  for should_upload in (True, False):
    yield api.test(
        'experimental%s' % ('_upload' if should_upload else ''),
        api.buildbucket.ci_build(
            builder='Linux Engine',
            git_repo=GIT_REPO,
            project='flutter',
        ),
        collect_build_output,
        api.runtime(is_luci=True, is_experimental=True),
        api.properties(
            InputProperties(
                goma_jobs='1024',
                fuchsia_ctl_version='version:0.0.2',
                android_sdk_license='android_sdk_hash',
                android_sdk_preview_license='android_sdk_preview_hash',
                upload_packages=should_upload,
            )),
    )
  yield api.test(
      'clobber',
      api.buildbucket.ci_build(
          builder='Linux Host Engine',
          git_repo='https://github.com/flutter/engine',
          project='flutter'),
      collect_build_output,
      api.runtime(is_luci=True, is_experimental=True),
      api.properties(
          InputProperties(
              clobber=True,
              git_url='https://github.com/flutter/engine',
              goma_jobs='200',
              git_ref='refs/pull/1/head',
              fuchsia_ctl_version='version:0.0.2',
              build_host=True,
              build_fuchsia=True,
              build_android_aot=True,
              build_android_debug=True,
              build_android_vulkan=True,
              android_sdk_license='android_sdk_hash',
              android_sdk_preview_license='android_sdk_preview_hash')),
  )
  yield api.test(
      'pull_request',
      api.buildbucket.ci_build(
          builder='Linux Host Engine',
          git_repo='https://github.com/flutter/engine',
          project='flutter'),
      collect_build_output,
      api.runtime(is_luci=True, is_experimental=True),
      api.properties(
          InputProperties(
              clobber=False,
              git_url='https://github.com/flutter/engine',
              goma_jobs='200',
              git_ref='refs/pull/1/head',
              fuchsia_ctl_version='version:0.0.2',
              build_host=True,
              build_fuchsia=True,
              build_android_aot=True,
              build_android_debug=True,
              build_android_vulkan=True,
              android_sdk_license='android_sdk_hash',
              android_sdk_preview_license='android_sdk_preview_hash')),
  )
  yield api.test(
      'Linux Fuchsia failing test',
      api.platform('linux', 64),
      api.buildbucket.ci_build(
          builder='Linux Engine', git_repo=GIT_REPO, project='flutter'),
      api.step_data(
          'gn --fuchsia --fuchsia-cpu x64 --runtime-mode debug --no-lto',
          retcode=1),
      api.properties(
          InputProperties(
              clobber=False,
              goma_jobs='1024',
              fuchsia_ctl_version='version:0.0.2',
              build_host=False,
              build_fuchsia=True,
              build_android_aot=False,
              build_android_debug=False,
              build_android_vulkan=False,
              no_maven=False,
              upload_packages=True,
              android_sdk_license='android_sdk_hash',
              android_sdk_preview_license='android_sdk_preview_hash')),
      api.properties.environ(EnvProperties(SWARMING_TASK_ID='deadbeef')),
  )

# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import config
from recipe_engine.recipe_api import Property
from recipe_engine.types import freeze

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb

DEPS = [
  'build',
  'chromium',
  'codesearch',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/gsutil',
  'depot_tools/tryserver',
  'goma',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'recipe_engine/time',
]

# Defines the trybots and the mirrored CI builder
# The trybot will use the parameters from the mirrored CI builder.
# It has the following strcture:
# {
#   <mastername which contains the trybots>: {
#     <trybot name>: <mirred CI builder name, which should be one of builders
#                     from SPEC['builders']>,
#   }
# }
TRYBOT_SPEC = freeze({
    'tryserver.chromium.codesearch': {
        'gen-android-try': 'codesearch-gen-chromium-android',
        'gen-chromiumos-try': 'codesearch-gen-chromium-chromiumos',
        'gen-fuchsia-try': 'codesearch-gen-chromium-fuchsia',
        'gen-lacros-try': 'codesearch-gen-chromium-lacros',
        'gen-linux-try': 'codesearch-gen-chromium-linux',
        'gen-win-try': 'codesearch-gen-chromium-win',
    }
})

SPEC = freeze({
  # The builders have the following parameters:
  # - compile_targets: the compile targets.
  # - platform: The platform for which the code is compiled.
  # - experimental: Whether to mark Kythe uploads as experimental.
  # - sync_generated_files: Whether to sync generated files into a git repo.
  # - corpus: Kythe corpus to specify in the kzip.
  # - build_config: Kythe build config to specify in the kzip.
  # - gen_repo_branch: Which branch in the generated files repo to sync to.
  # - gen_repo_out_dir: Which directory under src/out to write gen files to.
  'builders': {
    'codesearch-gen-chromium-android': {
      'compile_targets': [
        'all',
      ],
      'platform': 'android',
      'sync_generated_files': True,
      'gen_repo_branch': 'master',
      # Generated files will end up in out/android-Debug/gen.
      'gen_repo_out_dir': 'android-Debug',
      'corpus': 'chromium.googlesource.com/chromium/src',
      'build_config': 'android',
    },
    'codesearch-gen-chromium-lacros': {
      'compile_targets': [
        'all',
      ],
      'platform': 'lacros',
      'sync_generated_files': True,
      'gen_repo_branch': 'master',
      'corpus': 'chromium.googlesource.com/chromium/src',
      'build_config': 'lacros',
    },
    'codesearch-gen-chromium-linux': {
      'compile_targets': [
        'all',
      ],
      'platform': 'linux',
      'sync_generated_files': True,
      'gen_repo_branch': 'master',
      'corpus': 'chromium.googlesource.com/chromium/src',
      'build_config': 'linux',
    },
    'codesearch-gen-chromium-fuchsia': {
      'compile_targets': [
        'all',
      ],
      'platform': 'fuchsia',
      # Don't sync generated files for Fuchsia until they're verified.
      'sync_generated_files': False,
      'gen_repo_branch': 'master',
      # Generated files will end up in out/fuchsia-Debug/gen.
      'gen_repo_out_dir': 'fuchsia-Debug',
      'corpus': 'chromium.googlesource.com/chromium/src',
      'build_config': 'fuchsia',
    },
    'codesearch-gen-chromium-chromiumos': {
      # TODO(emso): Get the below compile targets.
      # from the chromium_tests recipe module.
      # Compile targets used by the 'Linux ChromiumOS Full' builder (2016-12-16)
      'compile_targets': [
        'app_list_unittests',
        'base_unittests',
        'browser_tests',
        'chromeos_unittests',
        'components_unittests',
        'compositor_unittests',
        'content_browsertests',
        'content_unittests',
        'crypto_unittests',
        'dbus_unittests',
        'device_unittests',
        'gcm_unit_tests',
        'google_apis_unittests',
        'gpu_unittests',
        'interactive_ui_tests',
        'ipc_tests',
        'jingle_unittests',
        'media_unittests',
        'message_center_unittests',
        'nacl_loader_unittests',
        'net_unittests',
        'ppapi_unittests',
        'printing_unittests',
        'remoting_unittests',
        'sandbox_linux_unittests',
        'sql_unittests',
        'ui_base_unittests',
        'unit_tests',
        'url_unittests',
        'views_unittests',
      ],
      'platform': 'chromeos',
      'sync_generated_files': True,
      'gen_repo_branch': 'master',
      # Generated files will end up in out/chromeos-Debug/gen.
      'gen_repo_out_dir': 'chromeos-Debug',
      'corpus': 'chromium.googlesource.com/chromium/src',
      'build_config': 'chromeos',
    },
    'codesearch-gen-chromium-win': {
      'compile_targets': [
        'all',
      ],
      'platform': 'win',
      'sync_generated_files': True,
      'gen_repo_branch': 'master',
      # Generated files will end up in out/win-Debug/gen.
      'gen_repo_out_dir': 'win-Debug',
      'corpus': 'chromium.googlesource.com/chromium/src',
      'build_config': 'win',
    },
  },
})

PROPERTIES = {
    'root_solution_revision':
        Property(
            kind=str, help='The revision to checkout and build.', default=None),
    'root_solution_revision_timestamp':
        Property(
            kind=config.Single((int, float)),
            help='The commit timestamp of the revision to checkout and build, '
            'in seconds since the UNIX epoch.',
            default=None),
    'codesearch_mirror_revision':
        Property(
            kind=str,
            help='The revision for codesearch to use for kythe references. '
            'Uses root_solution_revision if not available.',
            default=None),
    'codesearch_mirror_revision_timestamp':
        Property(
            kind=config.Single((int, float)),
            help='The commit timestamp of the revision for codesearch to use, '
            'in seconds since the UNIX epoch. Uses '
            'root_solution_revision_timestamp if not available.',
            default=None),
}


def RunSteps(api, root_solution_revision, root_solution_revision_timestamp,
             codesearch_mirror_revision, codesearch_mirror_revision_timestamp):
  name_suffix = ''
  builder_id = api.chromium.get_builder_id()
  if api.tryserver.is_tryserver:
    name_suffix = ' (with patch)'
    builder = TRYBOT_SPEC.get(builder_id.master, {}).get(builder_id.builder)
    assert builder is not None, ('Could not find trybot %s:%s in TRYBOT_SPEC' %
                                 (builder_id.master, builder_id.builder))
  else:
    builder = builder_id.builder
  bot_config = SPEC.get('builders', {}).get(builder)
  assert bot_config is not None, ('Could not find builder %s in SPEC' % builder)
  platform = bot_config.get('platform', 'linux')
  experimental = bot_config.get('experimental', False)
  corpus = bot_config.get('corpus', 'chromium-linux')
  build_config = bot_config.get('build_config', '')
  targets = bot_config.get('compile_targets', [])
  gen_repo_branch = bot_config.get('gen_repo_branch', 'master')
  gen_repo_out_dir = bot_config.get('gen_repo_out_dir', '')

  api.codesearch.set_config(
      'chromium',
      COMPILE_TARGETS=targets,
      PLATFORM=platform,
      EXPERIMENTAL=experimental,
      SYNC_GENERATED_FILES=bot_config['sync_generated_files'],
      GEN_REPO_BRANCH=gen_repo_branch,
      GEN_REPO_OUT_DIR=gen_repo_out_dir,
      CORPUS=corpus,
      BUILD_CONFIG=build_config,
  )

  # Checkout the repositories that are needed for the compile.
  gclient_config = api.gclient.make_config('chromium_no_telemetry_dependencies')
  if platform == 'android':
    gclient_config.target_os = ['android']
  elif platform == 'chromeos':
    gclient_config.target_os = ['chromeos']
  elif platform == 'fuchsia':
    gclient_config.target_os = ['fuchsia']
  api.gclient.c = gclient_config

  api.gclient.apply_config('android_prebuilts_build_tools')

  checkout_dir = api.path['cache'].join('builder')
  with api.context(cwd=checkout_dir):
    update_step = api.bot_update.ensure_checkout(
        root_solution_revision=root_solution_revision)
  api.chromium.set_build_properties(update_step.json.output['properties'])

  # Remove the llvm-build directory, so that gclient runhooks will download
  # a new clang binary and not use the previous one downloaded by
  # api.codesearch.run_clang_tool().
  api.file.rmtree('llvm-build',
                  api.path['checkout'].join('third_party', 'llvm-build'))

  api.chromium.set_config('codesearch', BUILD_CONFIG='Debug')
  api.chromium.ensure_goma()
  # CHROME_HEADLESS makes sure that running 'gclient runhooks' doesn't require
  # entering 'y' to agree to a license.
  with api.context(env={'CHROME_HEADLESS': '1'}):
    api.chromium.runhooks(name='runhooks%s' % name_suffix)

  # Cleans up generated files. This is to prevent old generated files from
  # being left in the out directory. Note that this needs to be run *before*
  # generating the compilation database, otherwise some of the files generated
  # by that step may be deleted (if they've been unchanged for the past week).
  api.codesearch.cleanup_old_generated()

  api.codesearch.generate_compilation_database(
      targets, mastername=builder_id.master, buildername=builder_id.builder)
  api.codesearch.generate_gn_target_list()

  # Prepare Java Kythe output directory
  kzip_dir = api.codesearch.c.javac_extractor_output_dir
  api.file.ensure_directory('java kzip', kzip_dir)

  # If the compile fails, abort execution and don't upload the pack. When we
  # upload an incomplete (due to compile failures) pack to Kythe, it fails
  # validation and doesn't get pushed out anyway, so there's no point in
  # uploading at all.
  with api.context(
      env={
          'KYTHE_ROOT_DIRECTORY': api.path['checkout'],
          'KYTHE_OUTPUT_DIRECTORY': kzip_dir,
          'KYTHE_CORPUS': corpus
      }):
    raw_result = api.chromium.compile(
        targets,
        name='compile%s' % name_suffix,
        use_goma_module=True,
        out_dir='out',
        target=gen_repo_out_dir or 'Debug')
  if raw_result.status != common_pb.SUCCESS:
    return raw_result

  # Download and run the clang tool.
  api.codesearch.run_clang_tool()

  # Process annotations and add kythe metadata.
  api.codesearch.add_kythe_metadata()

  # Create the kythe index pack and upload it to google storage.
  api.codesearch.create_and_upload_kythe_index_pack(
      commit_hash=codesearch_mirror_revision or None,
      commit_timestamp=int(codesearch_mirror_revision_timestamp or
                           root_solution_revision_timestamp or api.time.time()))

  # Check out the generated files repo and sync the generated files
  # into this checkout. This may fail due to other builders pushing to the
  # remote repo at the same time, so we retry this 3 times before giving up.
  _RunStepWithRetry(api, api.codesearch.checkout_generated_files_repo_and_sync)


def _RunStepWithRetry(api, step_function, max_tries=3):
  failures = 0
  while failures < max_tries:
    try:
      step_function()
      break
    except api.step.StepFailure as f:
      failures += 1
      if failures == max_tries:
        raise # pragma: no cover
      else:
        api.step.active_result.presentation.step_text = f.reason_message()
        api.step.active_result.presentation.status = api.step.WARNING


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)

SAMPLE_GN_DESC_OUTPUT = '''
{
   "//ipc:mojom_constants__generator": {
      "args": [ "--use_bundled_pylibs", "generate", "-d", "../../", "-I", "../../", "-o", "gen", "--bytecode_path", "gen/mojo/public/tools/bindings", "--filelist={{response_file_name}}", "-g", "c++", "--typemap", "gen/ipc/mojom_constants__type_mappings" ],
      "deps": [ "//ipc:mojom_constants__parsed", "//ipc:mojom_constants__type_mappings", "//ipc:mojom_constants__verify_deps", "//mojo/public/tools/bindings:precompile_templates" ],
      "inputs": [ "//mojo/public/tools/bindings/generators/mojom_cpp_generator.py" ],
      "outputs": [ "//out/Debug/gen/ipc/constants.mojom.cc", "//out/Debug/gen/ipc/constants.mojom.h", "//out/Debug/gen/ipc/constants.mojom-test-utils.cc", "//out/Debug/gen/ipc/constants.mojom-test-utils.h" ],
      "public": "*",
      "script": "//mojo/public/tools/bindings/mojom_bindings_generator.py",
      "sources": [ "//ipc/constants.mojom" ],
      "testonly": false,
      "toolchain": "//build/toolchain/linux:clang_x64",
      "type": "action",
      "visibility": [ "//ipc:*" ]
   }
}
'''

def GenTests(api):
  for buildername, _ in SPEC['builders'].iteritems():
    yield api.test(
        'full_%s' % (_sanitize_nonalpha(buildername)),
        api.step_data(
            'generate gn target list',
            api.raw_io.stream_output(SAMPLE_GN_DESC_OUTPUT, stream='stdout')),
        api.properties.generic(buildername=buildername),
        api.runtime(is_luci=True, is_experimental=False),
    )

  for buildername, _ in SPEC['builders'].iteritems():
    yield api.test(
        'full_%s_with_revision' % (_sanitize_nonalpha(buildername)),
        api.step_data(
            'generate gn target list',
            api.raw_io.stream_output(SAMPLE_GN_DESC_OUTPUT, stream='stdout')),
        api.properties.generic(buildername=buildername),
        api.properties(
            root_solution_revision='a' * 40,
            root_solution_revision_timestamp=1531887759),
        api.runtime(is_luci=True, is_experimental=False),
    )

  yield api.test(
      'full_%s_with_patch' % _sanitize_nonalpha('gen-linux-try'),
      api.buildbucket.try_build(
          project='chromium',
          bucket='try',
          builder='gen-linux-try',
          git_repo='https://chromium.googlesource.com/chromium/src',
          change_number=91827,
          patch_set=1),
      api.step_data(
          'generate gn target list',
          api.raw_io.stream_output(SAMPLE_GN_DESC_OUTPUT, stream='stdout')),
      api.properties.generic(
          mastername='tryserver.chromium.codesearch',
          buildername='gen-linux-try'),
      api.runtime(is_luci=True, is_experimental=False),
  )

  yield api.test(
      'full_%s_delete_generated_files_fail' %
      _sanitize_nonalpha('codesearch-gen-chromium-win'),
      api.step_data('delete old generated files', retcode=1),
      api.step_data(
          'generate gn target list',
          api.raw_io.stream_output(SAMPLE_GN_DESC_OUTPUT, stream='stdout')),
      api.properties.generic(buildername='codesearch-gen-chromium-win'),
      api.runtime(is_luci=True, is_experimental=False),
  )

  yield api.test(
      'full_%s_compile_fail' %
      _sanitize_nonalpha('codesearch-gen-chromium-linux'),
      api.step_data('compile', retcode=1),
      api.properties.generic(buildername='codesearch-gen-chromium-linux'),
      api.runtime(is_luci=True, is_experimental=False),
  )

  yield api.test(
      'full_%s_translation_unit_fail' %
      _sanitize_nonalpha('codesearch-gen-chromium-chromiumos'),
      api.step_data('run translation_unit clang tool', retcode=2),
      api.step_data(
          'generate gn target list',
          api.raw_io.stream_output(SAMPLE_GN_DESC_OUTPUT, stream='stdout')),
      api.properties.generic(buildername='codesearch-gen-chromium-chromiumos'),
      api.runtime(is_luci=True, is_experimental=False),
  )

  yield api.test(
      'full_%s_generate_compile_database_fail' %
      _sanitize_nonalpha('codesearch-gen-chromium-chromiumos'),
      api.step_data('generate compilation database', retcode=1),
      api.properties.generic(buildername='codesearch-gen-chromium-chromiumos'),
      api.runtime(is_luci=True, is_experimental=False),
  )

  yield api.test(
      'full_%s_git_config_fail' %
      _sanitize_nonalpha('codesearch-gen-chromium-win'),
      api.step_data('set core.longpaths', retcode=1),
      api.step_data(
          'generate gn target list',
          api.raw_io.stream_output(SAMPLE_GN_DESC_OUTPUT, stream='stdout')),
      api.properties.generic(buildername='codesearch-gen-chromium-win'),
      api.runtime(is_luci=True, is_experimental=False),
  )

  yield api.test(
      'full_%s_sync_generated_files_fail' %
      _sanitize_nonalpha('codesearch-gen-chromium-linux'),
      api.step_data('sync generated files', retcode=1),
      api.step_data(
          'generate gn target list',
          api.raw_io.stream_output(SAMPLE_GN_DESC_OUTPUT, stream='stdout')),
      api.properties.generic(buildername='codesearch-gen-chromium-linux'),
      api.runtime(is_luci=True, is_experimental=False),
  )

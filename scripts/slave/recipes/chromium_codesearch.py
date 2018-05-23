# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.recipe_api import Property
from recipe_engine.types import freeze

DEPS = [
  'build',
  'chromium',
  'codesearch',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/gsutil',
  'goma',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]

SPEC = freeze({
  # The builders have the following parameters:
  # - compile_targets: the compile targets.
  # - platform: The platform for which the code is compiled.
  # - sync_generated_files: Whether to sync generated files into a git repo.
  # - corpus: Kythe corpus to generate index packs under.
  # - root: Kythe VName root to generate index packs under.
  # - gen_repo_branch: Which branch in the generated files repo to sync to.
  # - gen_repo_out_dir: Which directory under src/out to write gen files to.
  'builders': {
    'codesearch-gen-chromium-linux': {
      'gclient_config': 'chromium',
      'compile_targets': [
        'all',
      ],
      'platform': 'linux',
      'sync_generated_files': True,
      'gen_repo_branch': 'master',
      'corpus': 'chromium',
    },
    'codesearch-gen-chromium-chromiumos': {
      'gclient_config': 'chromium',
      # TODO(emso): Get the below compile targets.
      # from the chromium_tests recipe module.
      # Compile targets used by the 'Linux ChromiumOS Full' builder (2016-12-16)
      'compile_targets': [
        'app_list_unittests',
        'base_unittests',
        'browser_tests',
        'cacheinvalidation_unittests',
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
      'gen_repo_branch': 'chromiumos',
      'corpus': 'chromium',
    },
    'codesearch-gen-chromium-android': {
      'gclient_config': 'chromium',
      'compile_targets': [
        'all',
      ],
      'platform': 'android',
      'sync_generated_files': True,
      'gen_repo_branch': 'master',
      # Generated files will end up in out/chromium-android/Debug/gen.
      'gen_repo_out_dir': 'chromium-android',
      'corpus': 'chromium',
      'root': 'chromium-android',
    },
    'codesearch-gen-chromium-win': {
      'gclient_config': 'chromium',
      'compile_targets': [
        'all',
      ],
      'platform': 'win',
      # Don't push generated files to git until we've verified their contents.
      'sync_generated_files': False,
      'gen_repo_branch': 'win',
      # Generated files will end up in out/chromium-win/Debug/gen.
      # TODO(jsca): Re-enable this once we have a solution for midl.py failing
      # due to output subdirectory depth.
      # 'gen_repo_out_dir': 'chromium-win',
      'corpus': 'chromium',
      'root': 'chromium-win',
    },
  },
})

PROPERTIES = {
    'root_solution_revision': Property(
        kind=str,
        help="The revision to checkout and build.",
        default=None),
}

def RunSteps(api, root_solution_revision):
  buildername = api.properties.get('buildername')

  bot_config = SPEC.get('builders', {}).get(buildername)
  platform = bot_config.get('platform', 'linux')
  corpus = bot_config.get('corpus', 'chromium-linux')
  root = bot_config.get('root', '')
  targets = bot_config.get('compile_targets', [])
  gen_repo_branch = bot_config.get('gen_repo_branch', 'master')
  gen_repo_out_dir = bot_config.get('gen_repo_out_dir', '')
  joined_gen_repo_out_dir = api.path.join('out', gen_repo_out_dir)

  api.codesearch.set_config(
      'chromium',
      COMPILE_TARGETS=targets,
      PLATFORM=platform,
      SYNC_GENERATED_FILES=bot_config['sync_generated_files'],
      GEN_REPO_BRANCH=gen_repo_branch,
      GEN_REPO_OUT_DIR=gen_repo_out_dir,
      CORPUS=corpus,
      ROOT=root,
  )

  # Checkout the repositories that are either directly needed or should be
  # included in the source archive.
  assert bot_config.get('gclient_config'), 'gclient_config is required'
  gclient_config = api.gclient.make_config(bot_config['gclient_config'])
  if platform == 'android':
    gclient_config.target_os = ['android']
  elif platform == 'chromeos':
    gclient_config.target_os = ['chromeos']
  for name, url in api.codesearch.c.additional_repos.iteritems():
    solution = gclient_config.solutions.add()
    solution.name = name
    solution.url = url
  api.gclient.c = gclient_config
  update_step = api.bot_update.ensure_checkout(
      root_solution_revision=root_solution_revision)
  api.chromium.set_build_properties(update_step.json.output['properties'])

  # Remove the llvm-build directory, so that gclient runhooks will download
  # the pre-built clang binary and not use the locally compiled binary from
  # the 'compile translation_unit clang tool' step.
  api.file.rmtree('llvm-build',
                  api.path['checkout'].join('third_party', 'llvm-build'))

  api.chromium.set_config('codesearch', BUILD_CONFIG='Debug')
  api.chromium.ensure_goma()
  # CHROME_HEADLESS makes sure that running 'gclient runhooks' doesn't require
  # entering 'y' to agree to a license.
  with api.context(env={'CHROME_HEADLESS': '1'}):
    api.chromium.runhooks()

  # Cleans up generated files. This is to prevent old generated files from
  # being left in the out directory. Note that this needs to be run *before*
  # generating the compilation database, otherwise some of the files generated
  # by that step may be deleted (if they've been unchanged for the past week).
  api.codesearch.cleanup_old_generated()

  api.codesearch.generate_compilation_database(targets, platform)

  # If the compile fails, abort execution and don't upload the pack. When we
  # upload an incomplete (due to compile failures) pack to Kythe, it fails
  # validation and doesn't get pushed out anyway, so there's no point in
  # uploading at all.
  api.chromium.compile(targets, use_goma_module=True,
                       out_dir=joined_gen_repo_out_dir)

  if platform == 'chromeos':
    # Generate a compilation database for Linux at a temporary location, then
    # use this to filter the ChromeOS compilation database.
    try:
      temp_file = api.path.mkstemp(prefix='compdb_filter')
      api.codesearch.generate_compilation_database(
          targets, 'linux', output_file=temp_file)
      api.codesearch.filter_compilation(temp_file)
    finally:
      api.file.remove('remove temporary compilation database', temp_file)

  # Download and run the clang tool.
  api.codesearch.run_clang_tool()

  # Create the kythe index pack and upload it to google storage.
  api.codesearch.create_and_upload_kythe_index_pack()

  # Check out the generated files repo and sync the generated files
  # into this checkout.
  api.codesearch.checkout_generated_files_repo_and_sync()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for buildername, config in SPEC['builders'].iteritems():
    platform = config.get('platform')
    test = api.test('full_%s' % (_sanitize_nonalpha(buildername)))
    test += api.step_data('generate compilation database for %s' % platform,
                          stdout=api.raw_io.output_text('some compilation data'))
    if platform == 'chromeos':
      test += api.step_data('generate compilation database for linux',
                            stdout=api.raw_io.output_text('some compilation data'))
    test += api.properties.generic(buildername=buildername,
                                   mastername='chromium.infra.codesearch')

    yield test

  for buildername, config in SPEC['builders'].iteritems():
    platform = config.get('platform')
    test = api.test('full_%s_with_revision' % (_sanitize_nonalpha(buildername)))
    test += api.step_data('generate compilation database for %s' % platform,
                          stdout=api.raw_io.output_text('some compilation data'))
    if platform == 'chromeos':
      test += api.step_data('generate compilation database for linux',
                            stdout=api.raw_io.output_text('some compilation data'))
    test += api.properties.generic(buildername=buildername,
                                   mastername='chromium.infra.codesearch')
    test += api.properties(root_solution_revision="deadbeef")

    yield test

  yield (
    api.test(
        'full_%s_delete_generated_files_fail' %
        _sanitize_nonalpha('codesearch-gen-chromium-win')) +
    api.step_data('delete old generated files', retcode=1) +
    api.properties.generic(buildername='codesearch-gen-chromium-win',
                           mastername='chromium.infra.codesearch')
  )

  yield (
    api.test(
        'full_%s_compile_fail' %
        _sanitize_nonalpha('codesearch-gen-chromium-linux')) +
    api.step_data('generate compilation database for linux',
                  stdout=api.raw_io.output_text('some compilation data')) +
    api.step_data('compile', retcode=1) +
    api.properties.generic(buildername='codesearch-gen-chromium-linux',
                           mastername='chromium.infra.codesearch')
  )

  yield (
    api.test(
        'full_%s_translation_unit_fail' % _sanitize_nonalpha('codesearch-gen-chromium-chromiumos')) +
    api.step_data('generate compilation database for chromeos',
                  stdout=api.raw_io.output_text('some compilation data')) +
    api.step_data('generate compilation database for linux',
                  stdout=api.raw_io.output_text('some compilation data')) +
    api.step_data('run translation_unit clang tool', retcode=2) +
    api.properties.generic(buildername='codesearch-gen-chromium-chromiumos',
                           mastername='chromium.infra.codesearch')
  )

  yield (
    api.test(
        'full_%s_generate_compile_database_fail' %
        _sanitize_nonalpha('codesearch-gen-chromium-chromiumos')) +
    api.step_data('generate compilation database for chromeos',
                  stdout=api.raw_io.output_text('some compilation data'),
                  retcode=1) +
    api.properties.generic(buildername='codesearch-gen-chromium-chromiumos',
                           mastername='chromium.infra.codesearch')
  )

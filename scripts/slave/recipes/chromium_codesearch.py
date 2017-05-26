# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'build',
  'chromium',
  'codesearch',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
  'file',
  'goma',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]

SPEC = freeze({
  # The builders have the following parameters:
  # - compile_targets: the compile targets.
  # - package_filename: The prefix of the name of the source archive.
  # - platform: The platform for which the code is compiled.
  # - sync_generated_files: Whether to sync generated files into a git repo.
  # - corpus: Kythe corpus to generate index packs under.
  # - gen_repo_branch: Which branch in the generated files repo to sync to.
  'builders': {
    'codesearch-gen-chromium-linux': {
      'compile_targets': [
        'all',
      ],
      'package_filename': 'chromium-src',
      'platform': 'linux',
      'sync_generated_files': True,
      'gen_repo_branch': 'master',
      'corpus': 'chromium-linux',
    },
    'codesearch-gen-chromium-chromiumos': {
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
      'package_filename': 'chromiumos-src',
      'platform': 'chromeos',
      'sync_generated_files': True,
      'gen_repo_branch': 'chromiumos',
      'corpus': 'chromium-chromeos',
    },
    'codesearch-gen-chromium-android': {
      'compile_targets': [
        'all',
      ],
      'package_filename': 'chromium-android-src',
      'platform': 'android',
      'sync_generated_files': True,
      'gen_repo_branch': 'android',
      'corpus': 'chromium-android',
    },
  },
})

def RunSteps(api):
  buildername = api.properties.get('buildername')

  bot_config = SPEC.get('builders', {}).get(buildername)
  platform = bot_config.get('platform', 'linux')
  corpus = bot_config.get('corpus', 'chromium-linux')
  targets = bot_config.get('compile_targets', [])

  api.codesearch.set_config(
      'chromium',
      COMPILE_TARGETS=targets,
      PACKAGE_FILENAME=bot_config['package_filename'],
      PLATFORM=platform,
      SYNC_GENERATED_FILES=bot_config['sync_generated_files'],
      GEN_REPO_BRANCH=bot_config['gen_repo_branch'],
      CORPUS=corpus,
  )

  # Checkout the repositories that are either directly needed or should be
  # included in the source archive.
  gclient_config = api.gclient.make_config('chromium')
  if platform == 'android':
    gclient_config.target_os = ['android']
  for name, url in api.codesearch.c.additional_repos.iteritems():
    solution = gclient_config.solutions.add()
    solution.name = name
    solution.url = url
  api.gclient.c = gclient_config
  update_step = api.bot_update.ensure_checkout()
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

  result = api.codesearch.generate_compilation_database(targets, platform)

  try:
    api.chromium.compile(targets, use_goma_module=True)
  except api.step.StepFailure: # pragma: no cover
    # Even if compilation fails, the Grok indexer may still be able to extract
    # (almost) all cross references. And the downside of failing on compile
    # error is that Codesearch gets stale.
    pass

  # Copy the created output to the correct directory. When running the clang
  # tool, it is assumed by the scripts that the compilation database is in the
  # out/Debug directory, and named 'compile_commands.json'.
  api.codesearch.copy_compilation_output(result)

  if platform == 'chromeos':
    result = api.codesearch.generate_compilation_database(targets, 'linux')
    api.codesearch.filter_compilation(result)

  # Compile and build the clang tool
  api.codesearch.build_clang_tool()

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

  yield (
    api.test(
        'full_%s_fail' % _sanitize_nonalpha('codesearch-gen-chromium-chromiumos')) +
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
        'full_%s_gen_compile_fail' %
        _sanitize_nonalpha('codesearch-gen-chromium-chromiumos')) +
    api.step_data('generate compilation database for chromeos',
                  stdout=api.raw_io.output_text('some compilation data'),
                  retcode=1) +
    api.properties.generic(buildername='codesearch-gen-chromium-chromiumos',
                           mastername='chromium.infra.codesearch')
  )

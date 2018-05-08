# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from recipe_engine.recipe_api import Property
from recipe_engine.types import freeze

DEPS = [
  'chromium',
  'codesearch',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
  'goma',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]

BUILDERS = freeze({
  # The builders have the following parameters:
  # - compile_targets: the compile targets.
  # - package_filename: The prefix of the name of the source archive.
  # - platform: The platform for which the code is compiled.
  # - sync_generated_files: Whether to sync generated files into a git repo.
  # - corpus: Kythe corpus to generate index packs under.
  # - gen_repo_branch: Which branch in the generated files repo to sync to.
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
  'codesearch-gen-chromium-win': {
    'compile_targets': [
      'all',
    ],
    'package_filename': 'chromium-src',
    'platform': 'win',
    'sync_generated_files': True,
    'gen_repo_branch': 'win',
    'corpus': 'chromium-win',
  },
})

PROPERTIES = {
  'buildername': Property(),
}

def RunSteps(api, buildername):
  builder = BUILDERS[buildername]

  platform = builder.get('platform', 'linux')
  corpus = builder.get('corpus', 'chromium-linux')
  targets = builder.get('compile_targets', [])

  api.codesearch.set_config(
      'chromium',
      COMPILE_TARGETS=targets,
      PACKAGE_FILENAME=builder['compile_targets'],
      PLATFORM=platform,
      SYNC_GENERATED_FILES=builder['sync_generated_files'],
      GEN_REPO_BRANCH=builder['gen_repo_branch'],
      CORPUS=corpus,
  )

  # Checkout the repositories that are either directly needed or should be
  # included in the source archive.
  gclient_config = api.gclient.make_config('chromium')
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
  api.chromium.runhooks()

  result = api.codesearch.generate_compilation_database(targets, platform)

  api.codesearch.cleanup_old_generated()

  try:
    api.chromium.compile(targets, use_goma_module=True)
  except api.step.StepFailure as _: # pragma: no cover
    # Even if compilation fails, the Kythe indexer may still be able to extract
    # (almost) all cross references. And the downside of failing on compile
    # error is that Codesearch gets stale.
    pass

  # Copy the created output to the correct directory.
  api.codesearch.copy_compilation_output(result)

  # Download and run the clang tool.
  api.codesearch.run_clang_tool()

  # Create the kythe index pack and upload it to google storage.
  api.codesearch.create_and_upload_kythe_index_pack()

  # Check out the generated files repo and sync the generated files
  # into this checkout.
  api.codesearch.checkout_generated_files_repo_and_sync()

def GenTests(api):
  sanitize = lambda s: ''.join(c if c.isalnum() else '_' for c in s)

  for buildername in BUILDERS:
    yield (api.test('%s_test_basic' % sanitize(buildername)) +
           api.properties.generic(buildername=buildername))

  yield (
    api.test(
        '%s_delete_generated_files_fail' %
        sanitize('codesearch-gen-chromium-win')) +
    api.step_data('delete old generated files', retcode=1) +
    api.properties.generic(buildername='codesearch-gen-chromium-win')
  )

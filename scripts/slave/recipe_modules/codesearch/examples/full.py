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
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/runtime',
  'recipe_engine/step',
]

BUILDERS = freeze({
  # The builders have the following parameters:
  # - compile_targets: the compile targets.
  # - platform: The platform for which the code is compiled.
  # - sync_generated_files: Whether to sync generated files into a git repo.
  # - corpus: Kythe corpus to generate index packs under.
  # - gen_repo_branch: Which branch in the generated files repo to sync to.
  'codesearch-gen-chromium-linux': {
    'compile_targets': [
      'all',
    ],
    'platform': 'linux',
    'sync_generated_files': True,
    'gen_repo_branch': 'master',
    'corpus': 'chromium-linux',
  },
  'codesearch-gen-chromium-win': {
    'compile_targets': [
      'all',
    ],
    'platform': 'win',
    'sync_generated_files': True,
    'gen_repo_branch': 'win',
    'gen_repo_out_dir': 'win-Debug',
    'corpus': 'chromium-win',
  },
})

def RunSteps(api):
  buildername = api.buildbucket.builder_name
  builder = BUILDERS[buildername]

  platform = builder.get('platform', 'linux')
  corpus = builder.get('corpus', 'chromium-linux')
  targets = builder.get('compile_targets', [])
  gen_repo_out_dir = builder.get('gen_repo_out_dir', '')

  api.codesearch.set_config(
      'chromium',
      COMPILE_TARGETS=targets,
      PLATFORM=platform,
      SYNC_GENERATED_FILES=builder['sync_generated_files'],
      GEN_REPO_BRANCH=builder['gen_repo_branch'],
      GEN_REPO_OUT_DIR=gen_repo_out_dir,
      CORPUS=corpus,
  )

  # Checkout the repositories that are needed for the compile.
  api.gclient.c = api.gclient.make_config('chromium_no_telemetry_dependencies')
  update_step = api.bot_update.ensure_checkout()
  api.chromium.set_build_properties(update_step.json.output['properties'])

  # Remove the llvm-build directory, so that gclient runhooks will download
  # a new clang binary and not use the previous one downloaded by
  # api.codesearch.run_clang_tool().
  api.file.rmtree('llvm-build',
                  api.path['checkout'].join('third_party', 'llvm-build'))

  api.chromium.set_config('codesearch', BUILD_CONFIG='Debug')
  api.chromium.ensure_goma()
  api.chromium.runhooks()

  api.codesearch.generate_compilation_database(
      targets, mastername='chromium.infra.codesearch',
      buildername=buildername)
  api.codesearch.generate_gn_target_list()

  api.codesearch.cleanup_old_generated()

  try:
    api.chromium.compile(targets, use_goma_module=True)
  except api.step.StepFailure as _: # pragma: no cover
    # Even if compilation fails, the Kythe indexer may still be able to extract
    # (almost) all cross references. And the downside of failing on compile
    # error is that Codesearch gets stale.
    pass

  # Download and run the clang tool.
  api.codesearch.run_clang_tool()

  # Create the kythe index pack and upload it to google storage.
  api.codesearch.create_and_upload_kythe_index_pack(commit_timestamp=1337000000)

  # Check out the generated files repo and sync the generated files
  # into this checkout.
  api.codesearch.checkout_generated_files_repo_and_sync()

def GenTests(api):
  sanitize = lambda s: ''.join(c if c.isalnum() else '_' for c in s)

  for buildername in BUILDERS:
    yield (api.test('%s_test_basic' % sanitize(buildername)) +
           api.properties.generic(buildername=buildername) +
           api.runtime(is_luci=True, is_experimental=False))
    yield (api.test('%s_test_experimental' % sanitize(buildername)) +
           api.properties.generic(buildername=buildername) +
           api.runtime(is_luci=True, is_experimental=True))

  yield (
    api.test(
        '%s_delete_generated_files_fail' %
        sanitize('codesearch-gen-chromium-win')) +
    api.step_data('delete old generated files', retcode=1) +
    api.properties.generic(buildername='codesearch-gen-chromium-win') +
    api.runtime(is_luci=True, is_experimental=False)
  )

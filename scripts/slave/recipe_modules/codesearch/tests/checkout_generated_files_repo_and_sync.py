# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'codesearch',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.gclient.set_config('chromium')
  update_step = api.bot_update.ensure_checkout()
  api.chromium.set_build_properties(update_step.json.output['properties'])
  api.codesearch.set_config(
      api.properties.get('codesearch_config', 'chromium'),
      COMPILE_TARGETS=api.properties.get('compile_targets', ['all']),
      PACKAGE_FILENAME=api.properties.get('package_filename', 'chromium-src'),
      PLATFORM=api.properties.get('platform', 'linux'),
      SYNC_GENERATED_FILES=api.properties.get('sync_generated_files', True),
      GEN_REPO_BRANCH=api.properties.get('gen_repo_branch', 'master'),
      GEN_REPO_OUT_DIR=api.properties.get('gen_repo_out_dir', ''),
      CORPUS=api.properties.get('corpus', 'chromium-linux'),
  )
  api.codesearch.checkout_generated_files_repo_and_sync()


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123)
  )

  yield (
      api.test('specified_branch_and_out_dir') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          gen_repo_branch='android',
          gen_repo_out_dir='chromium-android')
  )

  yield (
      api.test('false_sync_generated_files') +
      api.properties(
          buildername='test_buildername',
          buildnumber=123,
          sync_generated_files=False)
  )

  yield (
      api.test('generated_repo_not_set_failed') +
      api.properties(codesearch_config='base') +
      api.expect_exception('AssertionError')
  )

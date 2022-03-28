# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY3"

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
  properties = update_step.json.output['properties']
  kythe_commit_hash = 'a' * 40
  if api.properties.get('set_kythe_commit_hash_to_none'):
    kythe_commit_hash = None
  if api.properties.get('set_got_revision_cp_to_none'):
    properties.pop('got_revision_cp', 0)
  api.chromium.set_build_properties(properties)
  api.codesearch.set_config(
      api.properties.get('codesearch_config', 'chromium'),
      PROJECT=api.properties.get('project', 'chromium'),
      PLATFORM=api.properties.get('platform', 'linux'),
      SYNC_GENERATED_FILES=api.properties.get('sync_generated_files', True),
      GEN_REPO_BRANCH=api.properties.get('gen_repo_branch', 'main'),
      CORPUS=api.properties.get('corpus', 'chromium'),
      ROOT=api.properties.get('root', 'linux'),
  )
  api.codesearch.create_and_upload_kythe_index_pack(
      commit_hash=kythe_commit_hash, commit_timestamp=1337000000)


def GenTests(api):
  yield api.test('basic')

  yield api.test(
      'basic_chromium',
      api.properties(codesearch_config='chromium', project='chromium'),
  )

  yield api.test(
      'basic_chromiumos',
      api.properties(codesearch_config='chromiumos', project='chromiumos'),
  )

  yield api.test(
      'without_kythe_revision',
      api.properties(set_kythe_commit_hash_to_none=True),
  )

  yield api.test(
      'bucket_name_not_set_failed',
      api.properties(codesearch_config='base'),
      api.expect_exception('AssertionError'),
  )

  yield api.test(
      'basic_without_got_revision_cp',
      api.properties(set_got_revision_cp_to_none=True),
  )

  yield api.test(
      'basic_without_kythe_root',
      api.properties(root=''),
  )

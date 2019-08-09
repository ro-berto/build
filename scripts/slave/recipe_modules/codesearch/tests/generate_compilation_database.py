# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium',
  'codesearch',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.codesearch.set_config(
      api.properties.get('codesearch_config', 'chromium'),
      COMPILE_TARGETS=api.properties.get('compile_targets', ['all']),
      PLATFORM=api.properties.get('platform', 'linux'),
      SYNC_GENERATED_FILES=api.properties.get('sync_generated_files', True),
      GEN_REPO_BRANCH=api.properties.get('gen_repo_branch', 'master'),
      CORPUS=api.properties.get('corpus', 'chromium-linux'),
  )
  _, raw_result = api.codesearch.generate_compilation_database(
    api.codesearch.c.COMPILE_TARGETS,
    mastername='test_mastername',
    buildername='test_buildername')
  return raw_result


def GenTests(api):
  yield api.test('basic')

  yield (
      api.test('generate_compilation_database_failed') +
      api.step_data('generate compilation database', retcode=1)
  )

  yield (
    api.test('mb_gen_failed') +
    api.step_data('generate build files', retcode=1) +
    api.post_process(post_process.StatusFailure) +
    api.post_process(post_process.DropExpectation)
  )

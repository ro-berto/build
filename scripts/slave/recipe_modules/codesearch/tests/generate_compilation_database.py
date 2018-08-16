# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

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
  api.codesearch.generate_compilation_database(api.codesearch.c.COMPILE_TARGETS)


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(mastername='test_mastername',
                     buildername='test_buildername')
  )

  yield (
      api.test('generate_compilation_database_failed') +
      api.properties(mastername='test_mastername',
                     buildername='test_buildername') +
      api.step_data('generate compilation database', retcode=1)
  )

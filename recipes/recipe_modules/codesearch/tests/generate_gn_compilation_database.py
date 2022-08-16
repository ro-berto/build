# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY3"

DEPS = [
    'chromium',
    'codesearch',
    'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config('chromium')
  api.codesearch.set_config(
      api.properties.get('codesearch_config', 'chromium'),
      PROJECT=api.properties.get('project', 'chromium'),
      PLATFORM=api.properties.get('platform', 'webview'),
      SYNC_GENERATED_FILES=api.properties.get('sync_generated_files', True),
      GEN_REPO_BRANCH=api.properties.get('gen_repo_branch', 'main'),
      CORPUS=api.properties.get('corpus', 'chromium-linux'),
  )
  api.codesearch.generate_gn_compilation_database(
      targets=api.properties.get('targets'),
      builder_group='test_group',
      buildername='test_builder')


def GenTests(api):
  yield api.test(
      'basic', api.properties(targets=['//android_webview:system_webview_apk']))

  yield api.test(
      'generate_gn_compilation_database_failed',
      api.step_data('generate gn compilation database', retcode=1),
  )

  yield api.test('all_targets')

# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from recipe_engine.types import freeze

DEPS = [
  'archive',
  'chromedriver',
  'chromium',
  'chromium_android',
  'commit_position',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/json',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'recipe_engine/step',
]

BUILDERS = freeze({
  'Android ChromeDriver Tests Example': {
    'chromedriver_platform': 'android',
    # Whether or not to update the test results log (Android only).
    'update_test_log': True,
    'android_packages': [
      'chrome_shell',
      'chrome_stable',
      'chrome_beta',
      'chromedriver_webview_shell',
    ],
  },
})

def RunSteps(api):
  buildername = api.properties['buildername']
  builder = BUILDERS[buildername]
  android_packages = builder.get('android_packages')
  update_test_log = builder.get('update_test_log')

  api.chromium.set_config('chromium')
  api.gclient.set_config('chromium')
  api.bot_update.ensure_checkout()
  platform = builder.get('chromedriver_platform')

  commit_position = api.commit_position.parse_revision(
      api.properties['got_revision_cp'])

  if platform == 'android':
    api.chromedriver.download_prebuilts()

  passed = True
  try:
    api.chromedriver.run_all_tests(android_packages=android_packages,
                                   archive_server_logs=True)
  except api.step.StepFailure:
    passed = False

  if platform == 'android':
    if update_test_log:
      api.chromedriver.update_test_results_log(
          platform, commit_position, passed)

def GenTests(api):

  sanitize = lambda s: ''.join(c if c.isalnum() else '_' for c in s)

  yield (
      api.test('%s_basic' % sanitize('Android ChromeDriver')) +
      api.properties.generic(
          buildername='Android ChromeDriver Tests Example',
          slavename='slavename') +
      api.properties(
          parent_build_archive_url='gs://test-domain/test-archive.zip',
          got_revision_cp='refs/heads/master@{#3333333333}'))

  yield (
      api.test('%s_test_failure' % sanitize('Android ChromeDriver')) +
      api.properties.generic(
          buildername='Android ChromeDriver Tests Example',
          slavename='slavename') +
      api.properties(
          parent_build_archive_url='gs://test-domain/test-archive.zip',
          got_revision_cp='refs/heads/master@{#3333333333}') +
      api.step_data('java_tests chrome_stable.Run Tests', retcode=1))

  yield (
      api.test('%s_commit_already_in_logs' % sanitize('Android ChromeDriver')) +
      api.properties.generic(
          buildername='Android ChromeDriver Tests Example',
          slavename='slavename') +
      api.properties(
          parent_build_archive_url='gs://test-domain/test-archive.zip',
          got_revision_cp='refs/heads/master@{#3333333333}') +
      api.step_data('Download Test Results Log.read results log file',
                    api.raw_io.output_text('{"3333333333": true}')))

  yield (
      api.test('%s_download_logs_failure' % sanitize('Android ChromeDriver')) +
      api.properties.generic(
          buildername='Android ChromeDriver Tests Example',
          slavename='slavename') +
      api.properties(
          parent_build_archive_url='gs://test-domain/test-archive.zip',
          got_revision_cp='refs/heads/master@{#3333333333}') +
      api.step_data(
          'Download Test Results Log.gsutil download results log', retcode=1))

  yield (
      api.test('%s_unexpected_prebuilt' % sanitize('Android ChromeDriver')) +
      api.properties.generic(
          buildername='Android ChromeDriver Tests Example',
          slavename='slavename') +
      api.properties(
          parent_build_archive_url='gs://test-domain/test-archive.zip',
          got_revision_cp='refs/heads/master@{#3333333333}') +
      api.step_data(
          'Download Prebuilts.listdir get prebuilt filename',
          api.json.output(['rNone.zip'])))

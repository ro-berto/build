# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api
from recipe_engine.types import freeze

DEPS = [
  'adb',
  'archive',
  'chromedriver',
  'chromium',
  'chromium_android',
  'commit_position',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]

BUILDERS = freeze({
  'chromium.fyi': {
    'Android ChromeDriver Tests (dbg)': {
      'chromedriver_platform': 'android',
      'config': 'main_builder',
      'target': 'Debug',
      'update_test_log': True,
      'android_packages': [
        'chrome_beta',
        'chrome_stable',
        'chromedriver_webview_shell',
        'chromium',
      ],
      'install_apks': [
        'ChromeDriverWebViewShell.apk',
        'ChromePublic.apk',
      ],
    },
  },
})

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

def RunSteps(api):
  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  builder = BUILDERS[mastername][buildername]
  api.chromium_android.configure_from_properties(
      builder['config'],
      REPO_NAME='src',
      REPO_URL=REPO_URL,
      INTERNAL=False,
      BUILD_CONFIG=builder['target'])
  android_packages = builder.get('android_packages')
  update_test_log = builder.get('update_test_log')
  platform = builder.get('chromedriver_platform')

  api.gclient.set_config('chromium')
  api.gclient.apply_config('android')
  api.gclient.apply_config('chromedriver')
  api.bot_update.ensure_checkout()
  api.chromium.ensure_goma()
  api.chromium_android.clean_local_files()
  api.chromium.runhooks()
  api.chromium_android.run_tree_truth()

  api.archive.download_and_unzip_build(
      step_name='extract build',
      target=api.chromium.c.BUILD_CONFIG,
      build_url=None,
      build_archive_url=api.properties.get('parent_build_archive_url'))
  revision_cp = api.bot_update.last_returned_properties['got_revision_cp']
  commit_position = api.commit_position.parse_revision(revision_cp)

  api.chromium_android.common_tests_setup_steps(skip_wipe=True)
  if builder['install_apks']:
    for apk in builder['install_apks']:
      api.chromium_android.adb_install_apk(apk)
  api.chromedriver.download_prebuilts()

  passed = True
  try:
    api.chromedriver.run_all_tests(
        android_packages=android_packages,
        archive_server_logs=True)
  except api.step.StepFailure:
    passed = False
  if update_test_log:
    api.chromedriver.update_test_results_log(platform, commit_position, passed)

  api.chromium_android.common_tests_final_steps()

  if not passed:
    raise api.step.StepFailure('Test failures')

def GenTests(api):
  sanitize = lambda s: ''.join(c if c.isalnum() else '_' for c in s)

  yield (
      api.test('%s_basic' % sanitize('Android ChromeDriver Tests (dbg)')) +
      api.properties.generic(
          buildername='Android ChromeDriver Tests (dbg)',
          bot_id='bot_id',
          mastername='chromium.fyi') +
      api.properties(
          parent_build_archive_url='gs://test-domain/test-archive.zip',
          got_revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
          got_revision_cp='refs/heads/master@{#333333}'))

  yield (
      api.test(
          '%s_test_failure' % sanitize('Android ChromeDriver Tests (dbg)')) +
      api.properties.generic(
          buildername='Android ChromeDriver Tests (dbg)',
          bot_id='bot_id',
          mastername='chromium.fyi') +
      api.properties(
          parent_build_archive_url='gs://test-domain/test-archive.zip',
          got_revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
          got_revision_cp='refs/heads/master@{#333333}') +
      api.step_data('java_tests chrome_stable.Run Tests', retcode=1))

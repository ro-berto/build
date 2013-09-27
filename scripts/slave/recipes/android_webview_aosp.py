# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'android',
  'path',
  'properties',
  'rietveld'
]

def GenSteps(api):
  droid = api.android
  droid.set_config('AOSP')
  yield droid.chromium_with_trimmed_deps()
  yield droid.lastchange_steps()

  if 'issue' in api.properties:
    yield api.rietveld.apply_issue(api.rietveld.calculate_issue_root())

  yield droid.repo_init_steps()
  yield droid.generate_local_manifest_step()
  yield droid.repo_sync_steps()

  yield droid.symlink_chromium_into_android_tree_step()
  yield droid.gyp_webview_step()

  # TODO(android): use api.chromium.compile for this
  yield droid.compile_step(
    build_tool='make-android',
    targets=['libwebviewchromium', 'android_webview_java'],
    use_goma=True)

def GenTests(api):
  yield api.test('basic') + api.properties.scheduled()

  yield (
    api.test('uses_android_repo') +
    api.properties.scheduled() +
    api.path.exists(
      api.path.slave_build('android-src', '.repo', 'repo', 'repo'))
  )

  yield (
    api.test('doesnt_sync_if_android_present') +
    api.properties.scheduled() +
    api.path.exists(api.path.slave_build('android-src'))
  )

  yield (
    api.test('does_delete_stale_chromium') +
    api.properties.scheduled() +
    api.path.exists(
      api.path.slave_build('android-src', 'external', 'chromium_org'))
  )

  yield (
    api.test('uses_goma_test') +
    api.properties.scheduled() +
    api.path.exists(api.path.build('goma'))
  )

  yield api.test('works_if_revision_not_present') + api.properties.generic()

  yield api.test('trybot') + api.properties.tryserver()

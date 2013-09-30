# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium_android',
  'properties',
  'json',
]

def GenSteps(api):
  droid = api.chromium_android
  yield droid.common_tree_setup_steps()
  if droid.c.apply_svn_patch:
    yield droid.apply_svn_patch()
  yield droid.download_build()
  yield droid.common_tests_setup_steps()
  yield droid.instrumentation_tests()
  yield droid.common_tests_final_steps()

def GenTests(api):
  bot_ids = ['main_tests', 'enormous_tests', 'try_instrumentation_tests',
             'x86_try_instrumentation_tests']

  for bot_id in bot_ids:
    props = api.properties(
      repo_name='src/repo',
      repo_url='svn://svn.chromium.org/chrome/trunk/src',
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      android_bot_id=bot_id,
      buildername='test_buildername',
      parent_buildername='parent_buildername',
      internal=True
    )
    if 'try_instrumentation_tests' in bot_id:
      props += api.properties(revision='')
      props += api.properties(parent_buildnumber=1357)
      props += api.properties(patch_url='try_job_svn_patch')

    yield (
      api.test(bot_id) +
      props +
      api.step_data(
        'get app_manifest_vars',
        api.json.output({
          'version_code': 10,
          'version_name': 'some_builder_1234',
          'build_id': 3333,
          'date_string': 6001
        })
      ) +
      api.step_data(
        'envsetup',
        api.json.output({
          'PATH': './',
          'GYP_DEFINES': 'my_new_gyp_def=aaa',
          'GYP_SOMETHING': 'gyp_something_value'
        })
      )
    )

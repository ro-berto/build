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
  internal = api.properties.get('internal')

  yield droid.init_and_sync()
  yield droid.envsetup()
  yield droid.clean_local_files()
  if internal:
    yield droid.run_tree_truth()
  yield droid.runhooks()
  if droid.c.apply_svn_patch:
    yield droid.apply_svn_patch()
  yield droid.compile()

  if droid.c.run_findbugs:
    yield droid.findbugs()
  if droid.c.run_lint:
    yield droid.lint()
  if droid.c.run_checkdeps:
    yield droid.checkdeps()

def GenTests(api):
  bot_ids = ['main_builder', 'component_builder', 'clang_builder',
             'x86_builder', 'klp_builder', 'try_builder', 'x86_try_builder']

  for bot_id in bot_ids:
    props = api.properties(
      repo_name='src/repo',
      repo_url='svn://svn.chromium.org/chrome/trunk/src',
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      android_bot_id=bot_id,
      buildername='builder_name',
      internal=True,
      patch_url=None
    )
    if 'try_builder' in bot_id:
      props += api.properties(revision='')
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

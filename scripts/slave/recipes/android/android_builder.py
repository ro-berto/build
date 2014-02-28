# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'chromium_android',
  'properties',
  'json',
  'path',
  'python',
]

def GenSteps(api):
  droid = api.chromium_android

  bot_id = api.properties['android_bot_id']
  droid.configure_from_properties(bot_id)

  internal = api.properties.get('internal')

  yield droid.init_and_sync()
  yield droid.envsetup()
  yield droid.clean_local_files()
  if internal and droid.c.run_tree_truth:
    yield droid.run_tree_truth()

  # TODO(iannucci): Remove when dartium syncs chromium to >= crrev.com/252649
  extra_env = {}
  if bot_id == 'dartium_builder':
    extra_env = {'GYP_CROSSCOMPILE': "1"}
  yield droid.runhooks(extra_env)

  if droid.c.apply_svn_patch:
    yield droid.apply_svn_patch()
  yield droid.compile()

  if droid.c.run_findbugs:
    yield droid.findbugs()
  if droid.c.run_lint:
    yield droid.lint()
  if droid.c.run_checkdeps:
    yield droid.checkdeps()

  if internal and droid.c.get_app_manifest_vars:
    yield droid.upload_build()
  yield droid.cleanup_build()

  if api.properties.get('android_bot_id') == "dartium_builder":
    yield api.python('dartium_test',
        api.path.slave_build('src', 'dart', 'tools',
                             'bots', 'dartium_android.py'),
        args = ['--build-products-dir',
                api.chromium.c.build_dir(api.chromium.c.build_config_fs)]
    )

def GenTests(api):
  bot_ids = ['main_builder', 'component_builder', 'clang_builder',
             'x86_builder', 'arm_builder', 'try_builder', 'x86_try_builder',
             'dartium_builder', 'mipsel_builder']

  for bot_id in bot_ids:
    props = api.properties(
      repo_name='src/repo',
      repo_url='svn://svn.chromium.org/chrome/trunk/src',
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      android_bot_id=bot_id,
      buildername='builder_name',
      buildnumber=1337,
      internal=True,
      deps_file='DEPS',
      managed=True,
    )
    if 'try_builder' in bot_id:
      props += api.properties(revision='refs/remotes/origin/master')
      props += api.properties(upload_tag=1337)
      props += api.properties(patch_url='try_job_svn_patch')

    # dartium_builder does not use any step_data
    if bot_id == 'dartium_builder':
      add_step_data = lambda p: p
    else:
      add_step_data = lambda p: p + api.chromium_android.default_step_data(api)

    yield add_step_data(api.test(bot_id) + props)

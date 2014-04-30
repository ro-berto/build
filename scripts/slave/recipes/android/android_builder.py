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

BUILDERS = {
  'Android ARM64 Builder (dbg)': {
    'recipe_config': 'arm64_builder',
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
      'REPO_NAME': 'src',
      'INTERNAL': False,
      'REPO_URL': 'svn://svn-mirror.golo.chromium.org/chrome/trunk/src',
      'deps_file': 'DEPS'
    }
  },
  'Android x64 Builder (dbg)': {
    'recipe_config': 'x64_builder',
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
      'REPO_NAME': 'src',
      'INTERNAL': False,
      'REPO_URL': 'svn://svn-mirror.golo.chromium.org/chrome/trunk/src',
      'deps_file': 'DEPS'
    }
  }
}

def GenSteps(api):
  buildername = api.properties.get('buildername')
  bot_config = BUILDERS.get(buildername)
  droid = api.chromium_android

  bot_id = ''
  internal = False
  if bot_config:
    default_kwargs = {
      'REPO_URL': 'https://chromium.googlesource.com/chromium/src.git',
      'INTERNAL': False,
      'REPO_NAME': 'src',
      'BUILD_CONFIG': 'Debug'
    }
    kwargs = bot_config.get('kwargs', {})
    droid.configure_from_properties(bot_config['recipe_config'],
      **dict(default_kwargs.items() + kwargs.items()))
  else:
    # Bots that don't belong to BUILDERS. We want to move away from this.
    internal = api.properties.get('internal')
    bot_id = api.properties['android_bot_id']
    droid.configure_from_properties(bot_id)

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

  if buildername == 'clang_release_builder':
    yield droid.upload_clusterfuzz()
  elif internal and droid.c.get_app_manifest_vars:
    yield droid.upload_build_for_tester()

  yield droid.cleanup_build()

  if api.properties.get('android_bot_id') == "dartium_builder":
    yield api.python('dartium_test',
                     api.path['slave_build'].join('src', 'dart', 'tools',
                                                  'bots', 'dartium_android.py'),
        args = ['--build-products-dir',
                api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)]
    )

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)

def GenTests(api):
  # non BUILDER bots
  bot_ids = ['main_builder', 'component_builder', 'clang_builder',
             'clang_release_builder', 'x86_builder', 'arm_builder',
             'try_builder', 'x86_try_builder', 'dartium_builder',
             'mipsel_builder']

  for bot_id in bot_ids:
    props = api.properties(
      repo_name='src/repo',
      repo_url='svn://svn.chromium.org/chrome/trunk/src',
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      android_bot_id=bot_id,
      buildername=bot_id,
      buildnumber=1337,
      internal=True,
      deps_file='DEPS',
      managed=True,
    )
    if 'try_builder' in bot_id:
      props += api.properties(revision='refs/remotes/origin/master')
      props += api.properties(patch_url='try_job_svn_patch')

    # dartium_builder does not use any step_data
    if bot_id == 'dartium_builder':
      add_step_data = lambda p: p
    else:
      add_step_data = lambda p: p + api.chromium_android.default_step_data(api)

    yield add_step_data(api.test(bot_id) + props)

  # tests bots in BUILDERS
  for buildername in BUILDERS:
    test = (
      api.test('full_%s' % _sanitize_nonalpha(buildername)) +
      api.properties.generic(buildername=buildername,
          repository='svn://svn.chromium.org/chrome/trunk/src')
    )
    yield test

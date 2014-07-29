# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'bot_update',
  'chromium',
  'chromium_android',
  'gclient',
  'isolate',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'test_utils',
]

# Different types of builds this recipe can do.
RECIPE_CONFIGS = {
  'chromeos_official': {
    'chromium_config': 'chromium_official',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
  'chromium': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
  },
  'chromium_android': {
    'chromium_config': 'android',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['android'],
  },
  'chromium_clang': {
    'chromium_config': 'chromium_clang',
    'gclient_config': 'chromium',
  },
  'chromium_chromeos': {
    'chromium_config': 'chromium',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
  },
  'chromium_chromeos_clang': {
    'chromium_config': 'chromium_clang',
    'chromium_apply_config': ['chromeos'],
    'gclient_config': 'chromium',
  },
  'chromium_ios_device': {
    'chromium_config': 'chromium_ios_device',
    'gclient_config': 'ios',
  },
  'chromium_ios_ninja': {
    'chromium_config': 'chromium_ios_ninja',
    'gclient_config': 'ios',
  },
  'chromium_ios_simulator': {
    'chromium_config': 'chromium_ios_simulator',
    'gclient_config': 'ios',
  },
  'chromium_no_goma': {
    'chromium_config': 'chromium_no_goma',
    'gclient_config': 'chromium',
  },
  'chromium_v8': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium',
    'gclient_apply_config': [
      'v8_bleeding_edge_git',
      'chromium_lkcr',
      'show_v8_revision',
    ],
  },
  'chromium_skia': {
    'chromium_config': 'chromium',
    'gclient_config': 'chromium_skia',
  },
  'official': {
    'chromium_config': 'chromium_official',
    'gclient_config': 'chromium',
    'gclient_apply_config': ['chrome_internal'],
  },
}


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = api.chromium.builders.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  master_config = master_dict.get('settings', {})
  recipe_config_name = bot_config['recipe_config']
  assert recipe_config_name, (
      'Unrecognized builder name %r for master %r.' % (
          buildername, mastername))
  recipe_config = RECIPE_CONFIGS[recipe_config_name]

  api.chromium.set_config(recipe_config['chromium_config'],
                          **bot_config.get('chromium_config_kwargs', {}))
  # Set GYP_DEFINES explicitly because chromium config constructor does
  # not support that.
  api.chromium.c.gyp_env.GYP_DEFINES.update(bot_config.get('GYP_DEFINES', {}))
  if bot_config.get('use_isolate'):
    api.isolate.set_isolate_environment(api.chromium.c)
  for c in recipe_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)
  for c in bot_config.get('chromium_apply_config', []):
    api.chromium.apply_config(c)
  api.gclient.set_config(recipe_config['gclient_config'],
                         **bot_config.get('gclient_config_kwargs', {}))
  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if 'android_config' in bot_config:
    api.chromium_android.set_config(
        bot_config['android_config'],
        **bot_config.get('chromium_config_kwargs', {}))

  bot_type = bot_config.get('bot_type', 'builder_tester')

  if bot_config.get('set_component_rev'):
    # If this is a component build and the main revision is e.g. blink, webrtc,
    # or v8, the custom deps revision of this component must be dynamically
    # set to either: (1) the revision of the builder if this is a tester,
    # (2) 'revision' from the waterfall or (3) 'HEAD' for forced builds with
    # unspecified 'revision'.
    # TODO(machenbach): Use parent_got_cr_revision on testers with component
    # builds to match also the chromium revision from the builder.
    component_rev = api.properties.get('revision', 'HEAD')
    if bot_type == 'tester':
      component_rev = api.properties.get('parent_got_revision', component_rev)
    dep = bot_config.get('set_component_rev')
    api.gclient.c.revisions[dep['name']] = dep['rev_str'] % component_rev

  if api.platform.is_win:
    api.chromium.taskkill()

  # Bot Update re-uses the gclient configs.
  update_step = api.bot_update.ensure_checkout()
  assert update_step.json.output['did_run']
  # HACK(dnj): Remove after 'crbug.com/398105' has landed
  api.chromium.set_build_properties(update_step.json.output['properties'])

  # Whatever step is run right before this line needs to emit got_revision.
  got_revision = update_step.presentation.properties['got_revision']

  if not bot_config.get('disable_runhooks'):
    api.chromium.runhooks(env=bot_config.get('runhooks_env', {}))

  test_spec_file = bot_config.get('testing', {}).get('test_spec_file',
                                                     '%s.json' % mastername)
  test_spec_path = api.path['checkout'].join('testing', 'buildbot',
                                             test_spec_file)
  test_spec_result = api.json.read(
      'read test spec',
      test_spec_path,
      step_test_data=lambda: api.json.test_api.output({}))
  test_spec_result.presentation.step_text = 'path: %s' % test_spec_path
  for test in bot_config.get('tests', []):
    test.set_test_spec(test_spec_result.json.output)

  api.chromium.cleanup_temp()

  if bot_type in ['builder', 'builder_tester']:
    compile_targets = set(bot_config.get('compile_targets', []))
    for test in bot_config.get('tests', []):
      compile_targets.update(test.compile_targets(api))
    for builder_dict in master_dict.get('builders', {}).itervalues():
      if builder_dict.get('parent_buildername') == buildername:
        for test in builder_dict.get('tests', []):
          compile_targets.update(test.compile_targets(api))

    api.chromium.compile(targets=sorted(compile_targets))
    api.chromium.checkdeps()

    if api.chromium.c.TARGET_PLATFORM == 'android':
      api.chromium_android.check_webview_licenses()
      api.chromium_android.findbugs()

  if bot_config.get('use_isolate'):
    test_args_map = {}
    test_spec = test_spec_result.json.output
    gtests_tests = test_spec.get(buildername, {}).get('gtest_tests', [])
    for test in gtests_tests:
      if isinstance(test, dict):
        test_args = test.get('args')
        test_name = test.get('test')
        if test_name and test_args:
          test_args_map[test_name] = test_args
    api.isolate.find_isolated_tests(api.chromium.output_dir)

  if bot_type == 'builder':
    api.archive.zip_and_upload_build(
        'package build',
        api.chromium.c.build_config_fs,
        api.archive.legacy_upload_url(
          master_config.get('build_gs_bucket'),
          extra_url_components=api.properties['mastername']),
        build_revision=got_revision)

  if bot_type == 'tester':
    # Protect against hard to debug mismatches between directory names
    # used to run tests from and extract build to. We've had several cases
    # where a stale build directory was used on a tester, and the extracted
    # build was not used at all, leading to confusion why source code changes
    # are not taking effect.
    #
    # The best way to ensure the old build directory is not used is to
    # remove it.
    api.path.rmtree(
      'build directory',
      api.chromium.c.build_dir.join(api.chromium.c.build_config_fs))

    api.archive.download_and_unzip_build(
      'extract build',
      api.chromium.c.build_config_fs,
      api.archive.legacy_download_url(
        master_config.get('build_gs_bucket'),
        extra_url_components=api.properties['mastername'],),
      build_revision=api.properties.get('parent_got_revision', got_revision)
      )

  if (api.chromium.c.TARGET_PLATFORM == 'android' and
      bot_type in ['tester', 'builder_tester']):
    api.chromium_android.common_tests_setup_steps()

  if not bot_config.get('do_not_run_tests') and bot_config.get('tests', None):
    def test_runner():
      tests = bot_config.get('tests', [])
      for t in tests:
        t.run(api, '')

    api.chromium.setup_tests(bot_type, test_runner)

  if (api.chromium.c.TARGET_PLATFORM == 'android' and
      bot_type in ['tester', 'builder_tester']):
    api.chromium_android.common_tests_final_steps()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername, master_config in api.chromium.builders.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config.get('parent_buildername') is None, (
            'Unexpected parent_buildername for builder %r on master %r.' %
                (buildername, mastername))

      test = (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(mastername=mastername,
                               buildername=buildername,
                               parent_buildername=bot_config.get(
                                   'parent_buildername')) +
        api.platform(bot_config['testing']['platform'],
                     bot_config.get(
                         'chromium_config_kwargs', {}).get('TARGET_BITS', 64))
      )
      if bot_config.get('parent_buildername'):
        test += api.properties(parent_got_revision='1111111')

      if bot_type in ['builder', 'builder_tester']:
        test += api.step_data('checkdeps', api.json.output([]))

      if mastername == 'client.v8':
        test += api.properties(revision='22135')

      yield test

  yield (
    api.test('dynamic_gtest') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder') +
    api.platform('linux', 64) +
    api.override_step_data('read test spec', api.json.output({
      'Linux Tests': {
        'gtest_tests': [
          'base_unittests',
          {'test': 'browser_tests', 'shard_index': 0, 'total_shards': 2},
        ],
      },
    }))
  )

  yield (
    api.test('dynamic_gtest_win') +
    api.properties.generic(mastername='chromium.win',
                           buildername='Win7 Tests (1)',
                           parent_buildername='Win Builder') +
    api.platform('win', 64) +
    api.override_step_data('read test spec', api.json.output({
      'Win7 Tests (1)': {
        'gtest_tests': [
          'aura_unittests',
          {'test': 'browser_tests', 'shard_index': 0, 'total_shards': 2},
        ],
      },
    }))
  )


  yield (
    api.test('arm') +
    api.properties.generic(mastername='chromium.fyi',
                           buildername='Linux ARM Cross-Compile') +
    api.platform('linux', 64) +
    api.override_step_data('read test spec', api.json.output({
      'Linux ARM Cross-Compile': {
        'compile_targets': ['browser_tests_run'],
        'gtest_tests': [{
          'test': 'browser_tests',
          'args': ['--gtest-filter', '*NaCl*'],
          'shard_index': 0,
          'total_shards': 1,
        }],
      },
    }))
  )

  yield (
    api.test('findbugs_failure') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Android Builder (dbg)') +
    api.platform('linux', 32) +
    api.step_data('findbugs', retcode=1)
  )

  yield (
    api.test('msan') +
    api.properties.generic(mastername='chromium.fyi',
                           buildername='Chromium Linux MSan',
                           parent_buildername='Chromium Linux MSan Builder') +
    api.platform('linux', 64) +
    api.override_step_data('read test spec', api.json.output({
      'Chromium Linux MSan': {
        'compile_targets': ['base_unittests'],
        'gtest_tests': ['base_unittests'],
      },
    }))
  )

  yield (
    api.test('buildnumber_zero') +
    api.properties.generic(mastername='chromium.linux',
                           buildername='Linux Tests',
                           parent_buildername='Linux Builder',
                           buildnumber=0) +
    api.platform('linux', 64) +
    api.override_step_data('read test spec', api.json.output({
      'Linux Tests': {
        'gtest_tests': [
          'base_unittests',
          {'test': 'browser_tests', 'shard_index': 0, 'total_shards': 2},
        ],
      },
    }))
  )

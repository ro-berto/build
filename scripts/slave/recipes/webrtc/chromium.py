# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building Chromium and running WebRTC-specific tests with special
# requirements that doesn't allow them to run in the main Chromium waterfalls.
# Also provide a set of FYI bots that builds Chromium with WebRTC ToT to provide
# pre-roll test results.

DEPS = [
  'archive',
  'bot_update',
  'chromium',
  'chromium_android',
  'chromium_tests',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'webrtc',
]


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = api.webrtc.BUILDERS.get(mastername, {})
  master_settings = master_dict.get('settings', {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, ('Unrecognized builder name "%r" for master "%r".' %
                      (buildername, mastername))
  recipe_config_name = bot_config['recipe_config']
  recipe_config = api.webrtc.RECIPE_CONFIGS.get(recipe_config_name)
  assert recipe_config, ('Cannot find recipe_config "%s" for builder "%r".' %
                         (recipe_config_name, buildername))

  api.webrtc.setup(bot_config, recipe_config,
                   master_settings.get('PERF_CONFIG'))

  bot_type = bot_config.get('bot_type', 'builder_tester')

  # These testers are triggered by a builder's build being available, but the
  # revisions are configured to be HEAD instead of the DEPS-pinned versions.
  # Override that and make sure the exact same set of revisions as the builder
  # used is synced.
  if mastername == 'chromium.webrtc.fyi' and bot_type == 'tester':
    path_props = {
      'src': 'parent_got_chromium_revision',
      'src/third_party/webrtc': 'parent_got_webrtc_revision',
      'src/third_party/libjingle/source/talk': 'parent_got_libjingle_revision',
    }
    for path, property_name in path_props.iteritems():
      assert api.properties.get(property_name), 'Missing %s' % property_name
      api.gclient.c.revisions[path] = api.properties[property_name]

  if api.platform.is_win:
    api.chromium.taskkill()

  # Bot Update re-uses the gclient configs.
  step_result = api.bot_update.ensure_checkout(force=True)
  got_revision = step_result.presentation.properties['got_revision']

  api.webrtc.cleanup()
  if not bot_config.get('disable_runhooks'):
    api.chromium.runhooks()

  if bot_type in ('builder', 'builder_tester'):
    run_gn = api.chromium.c.project_generator.tool == 'gn'
    if run_gn:
      api.chromium.run_gn(use_goma=True)

    compile_targets = recipe_config.get('compile_targets', [])
    api.chromium.compile(targets=compile_targets)
    if (mastername == 'chromium.webrtc.fyi' and not run_gn and
        api.chromium.c.TARGET_PLATFORM != 'android'):
      api.webrtc.sizes(got_revision)

  archive_revision = api.properties.get('parent_got_revision', got_revision)
  if bot_type == 'builder' and bot_config.get('build_gs_archive'):
    api.webrtc.package_build(
        api.webrtc.GS_ARCHIVES[bot_config['build_gs_archive']],
        archive_revision)

  if bot_type == 'tester':
    api.webrtc.extract_build(
        api.webrtc.GS_ARCHIVES[bot_config['build_gs_archive']],
        archive_revision)

  if bot_type in ('builder_tester', 'tester'):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      api.chromium_android.common_tests_setup_steps()
      api.chromium_android.run_test_suite(
          'content_browsertests',
          gtest_filter='WebRtc*')
      api.chromium_android.common_tests_final_steps()
    else:
      test_runner = lambda: api.webrtc.runtests(revision_number=got_revision)
      api.chromium_tests.setup_chromium_tests(test_runner)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  builders = api.webrtc.BUILDERS

  def generate_builder(mastername, buildername, revision=None,
                       failing_test=None, parent_got_revision=None,
                       suffix=None):
    suffix = suffix or ''
    bot_config = builders[mastername]['builders'][buildername]
    bot_type = bot_config.get('bot_type', 'builder_tester')

    if bot_type in ('builder', 'builder_tester'):
      assert bot_config.get('parent_buildername') is None, (
          'Unexpected parent_buildername for builder %r on master %r.' %
              (buildername, mastername))
    test = (
      api.test('%s_%s%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername), suffix)) +
      api.properties.generic(mastername=mastername,
                             buildername=buildername,
                             revision=revision,
                             parent_buildername=bot_config.get(
                                 'parent_buildername')) +
      api.platform(bot_config['testing']['platform'],
                   bot_config.get(
                       'chromium_config_kwargs', {}).get('TARGET_BITS', 64))
    )
    if bot_type == 'tester':
      parent_rev = parent_got_revision or revision
      test += api.properties(parent_got_revision=parent_rev)
      if mastername == 'chromium.webrtc.fyi':
        test += api.properties(parent_got_chromium_revision='c1051e10',
                               parent_got_webrtc_revision='7eb27c',
                               parent_got_libjingle_revision='11b11c61e')
    if failing_test:
      test += api.step_data(failing_test, retcode=1)

    return test

  for mastername in ('chromium.webrtc', 'chromium.webrtc.fyi'):
    master_config = builders[mastername]
    for buildername in master_config['builders'].keys():
      revision = '7eb27c' if mastername == 'chromium.webrtc.fyi' else 'c1051e10'
      yield generate_builder(mastername, buildername, revision)

  # Forced build (not specifying any revision) and failing tests.
  mastername = 'chromium.webrtc'
  yield generate_builder(mastername, 'Linux Builder', revision=None,
                         suffix='_forced')

  buildername = 'Linux Tester'
  yield generate_builder(mastername, buildername, revision=None,
                         suffix='_forced_invalid')
  yield generate_builder(mastername, buildername, revision='c1051e10',
                         failing_test='browser_tests', suffix='_failing_test')

  # Periodic scheduler triggered builds also don't contain revision.
  mastername = 'chromium.webrtc.fyi'
  yield generate_builder(mastername, 'Win Builder', revision=None,
                         suffix='_periodic_triggered')

  # Testers gets got_revision value from builder passed as parent_got_revision.
  yield generate_builder(mastername, 'Win7 Tester', revision=None,
                         parent_got_revision='7eb27c',
                         suffix='_periodic_triggered')

  # Builder+tester running in client.webrtc.fyi during preparations for Git.
  mastername = 'client.webrtc.fyi'
  yield generate_builder(mastername, 'Linux Chromium Builder',
                         revision='deadbeef')
  yield generate_builder(mastername, 'Linux Chromium Tester',
                         parent_got_revision='deadbeef')
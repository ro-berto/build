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
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'step_history',
  'webrtc',
]


def GenSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = api.webrtc.BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  assert bot_config, ('Unrecognized builder name "%r" for master "%r".' %
                      (buildername, mastername))
  recipe_config_name = bot_config['recipe_config']
  recipe_config = api.webrtc.RECIPE_CONFIGS[recipe_config_name]
  assert recipe_config, ('Invalid recipe_config "%s" for builder "%r".' %
                         (recipe_config_name, buildername))

  # The infrastructure team has recommended not to use git yet on the
  # bots, but it's very nice to have when testing locally.
  # To use, pass "use_git=True" as an argument to run_recipe.py.
  use_git = api.properties.get('use_git', False)

  api.webrtc.set_config(recipe_config['webrtc_config'])
  api.chromium.set_config(recipe_config['chromium_config'],
                          **bot_config.get('chromium_config_kwargs', {}))
  api.gclient.set_config(recipe_config['gclient_config'], GIT_MODE=use_git)
  for c in recipe_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if api.platform.is_win:
    yield api.chromium.taskkill()

  revision = api.properties.get('revision')
  assert revision, 'Revision must be specified as the "revision" property.'

  # The chromium.webrtc.fyi master is used as an early warning system to catch
  # WebRTC specific errors before they get rolled into Chromium's DEPS.
  # Therefore this waterfall needs to build src/third_party/webrtc with WebRTC
  # ToT and use the Chromium HEAD. The revision poller is passing a WebRTC
  # revision for these recipes.
  if mastername == 'chromium.webrtc.fyi':
    s = api.gclient.c.solutions
    s[0].revision = 'HEAD'
    s[0].custom_vars['webrtc_revision'] = revision

  # Bot Update re-uses the gclient configs.
  yield api.bot_update.ensure_checkout(),
  if not api.step_history.last_step().json.output['did_run']:
    yield api.gclient.checkout(),

  bot_type = bot_config.get('bot_type', 'builder_tester')

  if not bot_config.get('disable_runhooks'):
    yield api.chromium.runhooks()

  yield api.chromium.cleanup_temp()

  # Instead of yielding single steps or groups of steps, yield all at the end.
  steps = []

  if bot_type in ['builder', 'builder_tester']:
    compile_targets = recipe_config.get('compile_targets', [])
    steps.append(api.chromium.compile(targets=compile_targets))

  if bot_type == 'builder':
    steps.append(api.webrtc.package_build(
        api.webrtc.GS_ARCHIVES[bot_config['build_gs_archive']], revision))

  if bot_type == 'tester':
    # Ensure old build directory is not used is by removing it.
    steps.append(api.path.rmtree(
        'build directory',
        api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)))

    steps.append(api.webrtc.extract_build(
        api.webrtc.GS_ARCHIVES[bot_config['build_gs_archive']], revision))

  test_steps = api.webrtc.runtests(recipe_config.get('test_suite'))
  steps.extend(api.chromium.setup_tests(bot_type, test_steps))

  yield steps


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  for mastername in ('chromium.webrtc', 'chromium.webrtc.fyi'):
    master_config = api.webrtc.BUILDERS[mastername]
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config.get('parent_buildername') is None, (
            'Unexpected parent_buildername for builder %r on master %r.' %
                (buildername, mastername))

      webrtc_config_kwargs = bot_config.get('webrtc_config_kwargs', {})
      revision = '321321'
      if mastername == 'chromium.webrtc.fyi':
        revision = '12345'

      test = (
        api.test('%s_%s' % (_sanitize_nonalpha(mastername),
                            _sanitize_nonalpha(buildername))) +
        api.properties.generic(mastername=mastername,
                               buildername=buildername,
                               parent_buildername=bot_config.get(
                                   'parent_buildername'),
                               revision=revision) +
        api.platform(bot_config['testing']['platform'],
                     bot_config.get(
                         'chromium_config_kwargs', {}).get('TARGET_BITS', 64))
      )
      if webrtc_config_kwargs.get('MEASURE_PERF', False):
        test += api.properties(perf_id=_sanitize_nonalpha(buildername),
                               show_perf_results=True)
        if mastername == 'chromium.webrtc.fyi':
          # The WebRTC revision is the revision from the poller of this master
          # and needs this to be displayed properly on the perf dashboard.
          test += api.properties(perf_config={'a_default_rev': 'r_webrtc_rev'})

      yield test

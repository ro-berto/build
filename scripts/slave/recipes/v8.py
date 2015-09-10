# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

DEPS = [
  'archive',
  'chromium',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'raw_io',
  'step',
  'time',
  'tryserver',
  'v8',
]


def RunSteps(api):
  v8 = api.v8
  v8.apply_bot_config(v8.BUILDERS)

  if api.platform.is_win:
    api.chromium.taskkill()

  update_step = v8.checkout()

  if v8.c.mips_cross_compile:
    v8.setup_mips_toolchain()
  v8.runhooks()
  api.chromium.cleanup_temp()

  if v8.should_build:
    v8.compile()

  if v8.run_dynamorio:
    v8.dr_compile()

  if v8.should_upload_build:
    v8.upload_build()

  v8.maybe_create_clusterfuzz_archive(update_step)

  if v8.should_download_build:
    v8.download_build()

  if v8.should_test:
    test_results = v8.runtests()
    v8.maybe_bisect(test_results)

    if test_results.is_negative:
      # Let the overall build fail for failures and flakes.
      raise api.step.StepFailure('Failures or flakes in build.')

  v8.maybe_trigger()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  # Simulated branch names for testing. Optionally upgrade these in branch
  # period to reflect the real branches used by the gitiles poller.
  STABLE_BRANCH = '4.2'
  BETA_BRANCH = '4.3'
  ROLL_BRANCH = '4.4.42'

  def get_test_branch_name(mastername, buildername):
    if mastername == 'client.dart.fyi':
      return STABLE_BRANCH
    if re.search(r'stable branch', buildername):
      return STABLE_BRANCH
    if re.search(r'beta branch', buildername):
      return BETA_BRANCH
    if re.search(r'roll branch', buildername):
      return ROLL_BRANCH
    return 'master'

  for mastername, master_config in api.v8.BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      bot_type = bot_config.get('bot_type', 'builder_tester')

      if bot_type in ['builder', 'builder_tester']:
        assert bot_config['testing'].get('parent_buildername') is None

      branch = get_test_branch_name(mastername, buildername)
      v8_config_kwargs = bot_config.get('v8_config_kwargs', {})
      test = (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(mastername=mastername,
                               buildername=buildername,
                               branch=branch,
                               parent_buildername=bot_config.get(
                                   'parent_buildername'),
                               revision='20123') +
        api.platform(bot_config['testing']['platform'],
                     v8_config_kwargs.get('TARGET_BITS', 64))
      )

      if bot_config.get('parent_buildername'):
        test += api.properties(parent_got_revision='54321')

      if mastername.startswith('tryserver'):
        test += (api.properties(
            revision='12345',
            patch_url='svn://svn-mirror.golo.chromium.org/patch'))

      yield test

  yield (
    api.test('branch_sync_failure') +
    api.properties.tryserver(mastername='client.v8.branches',
                             buildername='V8 Linux - roll branch',
                             branch=ROLL_BRANCH,
                             revision='20123') +
    api.platform('linux', 32) +
    api.step_data('bot_update', retcode=1)
  )

  mastername = 'client.v8'
  buildername = 'V8 Linux - isolates'
  bot_config = api.v8.BUILDERS[mastername]['builders'][buildername]
  def TestFailures(wrong_results, flakes):
    results_suffix = "_wrong_results" if wrong_results else ""
    flakes_suffix = "_flakes" if flakes else ""
    return (
      api.test('full_%s_%s_test_failures%s%s' %
          (_sanitize_nonalpha(mastername),
          _sanitize_nonalpha(buildername),
          results_suffix,
          flakes_suffix)) +
      api.properties.generic(mastername=mastername,
                             buildername=buildername,
                             branch='master',
                             parent_buildername=bot_config.get(
                                 'parent_buildername')) +
      api.platform(bot_config['testing']['platform'],
                   v8_config_kwargs.get('TARGET_BITS', 64)) +
      api.v8(test_failures=True, wrong_results=wrong_results, flakes=flakes)
    )

  yield TestFailures(wrong_results=False, flakes=False)
  yield TestFailures(wrong_results=False, flakes=True)
  yield (
      TestFailures(wrong_results=True, flakes=False) +
      api.expect_exception('AssertionError')
  )
  yield (
    api.test('full_%s_%s_flaky_test_failures' % (
        _sanitize_nonalpha(mastername), _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername,
                           buildername=buildername,
                           branch='master',
                           parent_buildername=bot_config.get(
                               'parent_buildername')) +
    api.platform(bot_config['testing']['platform'],
                 v8_config_kwargs.get('TARGET_BITS', 64)) +
    api.override_step_data('Check - flaky', api.v8.one_failure())
  )

  yield (
    api.test('full_%s_%s_empty_json' % (
        _sanitize_nonalpha(mastername), _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername,
                           buildername=buildername,
                           branch='master',
                           parent_buildername=bot_config.get(
                               'parent_buildername')) +
    api.platform(bot_config['testing']['platform'],
                 v8_config_kwargs.get('TARGET_BITS', 64)) +
    api.override_step_data('Check - flaky', api.json.output([])) +
    api.expect_exception('AssertionError')
  )

  yield (
    api.test('full_%s_%s_one_failure' %
        (_sanitize_nonalpha(mastername),
        _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername,
                           buildername=buildername,
                           branch='master',
                           parent_buildername=bot_config.get(
                               'parent_buildername')) +
    api.platform(bot_config['testing']['platform'],
                 v8_config_kwargs.get('TARGET_BITS', 64)) +
    api.override_step_data('Check', api.v8.one_failure())
  )

  buildername = 'V8 Linux - memcheck'
  yield (
    api.test('full_%s_%s_no_errors' % (
        _sanitize_nonalpha(mastername), _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername,
                           buildername=buildername,
                           branch='master',
                           parent_buildername=bot_config.get(
                               'parent_buildername')) +
    api.platform(bot_config['testing']['platform'],
                 v8_config_kwargs.get('TARGET_BITS', 64)) +
    api.override_step_data(
        'Simple Leak Check',
        api.raw_io.stream_output('no leaks are possible', stream='stderr'),
    )
  )

  # Bisect over range a1, a2, a3. Assume a2 is the culprit. Steps:
  # Bisect a0 -> no failures.
  # Bisect a2 -> failures.
  # Bisect a1 -> no failures.
  # Report culprit a2.
  buildername = 'V8 Linux - predictable'
  yield (
    api.test('full_%s_%s_bisect' % (
        _sanitize_nonalpha(mastername), _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername,
                           buildername=buildername,
                           branch='master') +
    api.platform(bot_config['testing']['platform'],
                 v8_config_kwargs.get('TARGET_BITS', 64)) +
    api.override_step_data('Mjsunit', api.v8.bisect_failures_example()) +
    api.override_step_data(
        'Bisect a2.Retry', api.v8.bisect_failures_example()) +
    api.time.step(120)
  )

  # Disable bisection, because the failing test is too long compared to the
  # overall test time.
  yield (
    api.test('full_%s_%s_bisect_tests_too_long' % (
        _sanitize_nonalpha(mastername), _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername,
                           buildername=buildername,
                           branch='master') +
    api.platform(bot_config['testing']['platform'],
                 v8_config_kwargs.get('TARGET_BITS', 64)) +
    api.override_step_data('Mjsunit', api.v8.bisect_failures_example()) +
    api.time.step(7)
  )

  # Bisect over range a1, a2, a3. Assume a3 is the culprit. This is a tester
  # and the build for a2 is not available. Steps:
  # Bisect a0 -> no failures.
  # Bisect a1 -> no failures.
  # Report a2 and a3 as possible culprits.
  buildername = 'V8 Linux64 - debug - greedy allocator'
  bot_config = api.v8.BUILDERS[mastername]['builders'][buildername]
  yield (
    api.test('full_%s_%s_bisect_tester' % (
        _sanitize_nonalpha(mastername), _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername,
                           buildername=buildername,
                           branch='master',
                           parent_buildername=bot_config.get(
                               'parent_buildername')) +
    api.platform(bot_config['testing']['platform'],
                 v8_config_kwargs.get('TARGET_BITS', 64)) +
    api.override_step_data('Check', api.v8.bisect_failures_example()) +
    api.time.step(120)
  )

  # Disable bisection due to a recurring failure. Steps:
  # Bisect a0 -> failures.
  buildername = 'V8 Linux - predictable'
  yield (
    api.test('full_%s_%s_bisect_recurring_failure' % (
        _sanitize_nonalpha(mastername), _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername,
                           buildername=buildername,
                           branch='master') +
    api.platform(bot_config['testing']['platform'],
                 v8_config_kwargs.get('TARGET_BITS', 64)) +
    api.override_step_data('Mjsunit', api.v8.bisect_failures_example()) +
    api.override_step_data(
        'Bisect a0.Retry', api.v8.bisect_failures_example()) +
    api.time.step(120)
  )

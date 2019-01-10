# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This recipe can be used by components like v8 to verify blink tests with a
low false positive rate. Similar to a trybot, this recipe compares test
failures from a build with a current component revision with test failures
from a build with a pinned component revision.

Summary of the recipe flow:
1. Sync chromium to HEAD
2. Sync blink to HEAD
3. Sync component X to revision Y
4. Run blink tests
-> In case of failures:
5. Sync chromium to same revision as 1
6. Sync blink to same revision as 2
7. Sync component X to pinned revision from DEPS file
8. Run blink tests
-> If failures in 4 don't happen in 8, then revision Y reveals a problem not
   present in the pinned revision

Revision Y will be the revision property as provided by buildbot or HEAD (i.e.
in a forced build with no revision provided).
"""

from recipe_engine.types import freeze

DEPS = [
  'build/build',
  'build/chromium',
  'build/chromium_checkout',
  'build/chromium_tests',
  'build/test_utils',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
]


def V8Builder(config, bits, platform):
  return {
    'gclient_apply_config': ['show_v8_revision'],
    'chromium_apply_config': [],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': config,
      'TARGET_BITS': bits,
    },
    'additional_expectations': [
      'v8', 'tools', 'blink_tests', 'TestExpectations',
    ],
    'component': {'path': 'src/v8', 'revision': '%s'},
    'testing': {'platform': platform},
  }


BUILDERS = freeze({
  'client.v8.fyi': {
    'builders': {
      'V8-Blink Win': V8Builder('Release', 32, 'win'),
      'V8-Blink Mac': V8Builder('Release', 64, 'mac'),
      'V8-Blink Linux 64': V8Builder('Release', 64, 'linux'),
      'V8-Blink Linux 64 - future': V8Builder('Release', 64, 'linux'),
      'V8-Blink Linux 64 (dbg)': V8Builder('Debug', 64, 'linux'),
    },
  },
})


def determine_new_future_failures(caller_api, extra_args):
  tests = [
    caller_api.chromium_tests.steps.BlinkTest(
        extra_args=extra_args + [
          '--additional-expectations',
          caller_api.path['checkout'].join(
              'v8', 'tools', 'blink_tests', 'TestExpectationsFuture'),
          '--additional-driver-flag',
          '--js-flags=--future',
        ],
    ),
  ]

  # Since we don't implement 'retry with patch', we also set the flag on
  # BlinkTest.
  for test in tests:
    test._should_retry_with_patch = False

  failing_tests = caller_api.test_utils.run_tests_with_patch(caller_api, tests)
  if not failing_tests:
    return

  try:
    # HACK(machenbach): Blink tests store state about failing tests. In order
    # to rerun without future, we need to remove the extra args from the
    # existing test object.
    failing_tests[0]._extra_args = extra_args
    caller_api.test_utils.run_tests(caller_api, failing_tests, 'without patch')
  finally:
    with caller_api.step.defer_results():
      for t in failing_tests:
        caller_api.test_utils.summarize_test_with_patch_deapplied(
            caller_api, t, failure_is_fatal=True)


def determine_new_failures(caller_api, tests, deapply_patch_fn):
  """
  Utility function for running steps with a patch applied, and retrying
  failing steps without the patch. Failures from the run without the patch are
  ignored.

  Args:
    caller_api - caller's recipe API; this is needed because self.m here
                 is different than in the caller (different recipe modules
                 get injected depending on caller's DEPS vs. this module's
                 DEPS)
    tests - iterable of objects implementing the Test interface above
    deapply_patch_fn - function that takes a list of failing tests
                       and undoes any effect of the previously applied patch
  """
  # Convert iterable to list, since it is enumerated multiple times.
  tests = list(tests)

  # Since we don't implement 'retry with patch', we set the corresponding flag
  # on the Test instances.
  for test in tests:
    test._should_retry_with_patch = False

  failing_tests = caller_api.test_utils.run_tests_with_patch(caller_api, tests)
  if not failing_tests:
    return

  try:
    result = deapply_patch_fn(failing_tests)
    caller_api.test_utils.run_tests(caller_api, failing_tests, 'without patch')
    return result
  finally:
    with caller_api.step.defer_results():
      for t in failing_tests:
        caller_api.test_utils.summarize_test_with_patch_deapplied(
            caller_api, t, failure_is_fatal=True)

def RunSteps(api):
  mastername = api.properties.get('mastername')
  buildername = api.buildbucket.builder_name
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)

  # Sync chromium to HEAD.
  api.gclient.set_config('chromium', GIT_MODE=True)
  api.gclient.c.revisions['src'] = 'HEAD'
  api.chromium.set_config('blink',
                          **bot_config.get('chromium_config_kwargs', {}))

  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)
  api.chromium_tests.set_config('chromium')

  # Sync component to current component revision.
  component_revision = api.buildbucket.gitiles_commit.id or 'HEAD'
  api.gclient.c.revisions[bot_config['component']['path']] = (
      bot_config['component']['revision'] % component_revision)

  # Ensure we remember the chromium revision.
  api.gclient.c.got_revision_reverse_mapping['got_cr_revision'] = 'src'
  api.gclient.c.got_revision_mapping.pop('src', None)

  # Run all steps in the checkout dir (consistent with chromium_tests).
  with api.context(cwd=api.chromium_checkout.get_checkout_dir(bot_config)):
    step_result = api.bot_update.ensure_checkout()

    api.chromium.ensure_goma()

    with api.context(cwd=api.path['checkout']):
      api.chromium.runhooks()

    api.chromium_tests.run_mb_and_compile(
        ['blink_tests'], [],
        name_suffix=' (with patch)',
    )

    def component_pinned_fn(_failing_steps):
      bot_update_json = step_result.json.output
      api.gclient.c.revisions['src'] = str(
          bot_update_json['properties']['got_cr_revision'])
      # Reset component revision to the pinned revision from chromium's DEPS
      # for comparison.
      del api.gclient.c.revisions[bot_config['component']['path']]
      # Update without changing got_revision. The first sync is the revision
      # that is tested. The second is just for comparison. Setting got_revision
      # again confuses the waterfall's console view.
      api.bot_update.ensure_checkout(
          ignore_input_commit=True, update_presentation=False)

      api.chromium_tests.run_mb_and_compile(
          ['blink_tests'], [],
          name_suffix=' (without patch)',
      )

    # TODO(machenbach): Temporarily use higher timeout until builder migrates to
    # swarming.
    extra_args = ['--time-out-ms=12000']
    if bot_config.get('additional_expectations'):
      extra_args.extend([
        '--additional-expectations',
        api.path['checkout'].join(*bot_config['additional_expectations']),
      ])

    tests = [
      api.chromium_tests.steps.BlinkTest(extra_args=extra_args),
    ]

    if 'future' in buildername:
      determine_new_future_failures(api.chromium_tests.m, extra_args)
    else:
      determine_new_failures(api.chromium_tests.m, tests, component_pinned_fn)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  canned_test = api.test_utils.canned_test_output
  with_patch = 'blink_web_tests (with patch)'
  without_patch = 'blink_web_tests (without patch)'

  def properties(mastername, buildername):
    return (
      api.properties.generic(mastername=mastername, path_config='kitchen') +
      api.buildbucket.ci_build(
          project='v8',
          git_repo='https://chromium.googlesource.com/v8/v8',
          builder=buildername,
          revision='a' * 40)
    )

  for mastername, master_config in BUILDERS.iteritems():
    for buildername, bot_config in master_config['builders'].iteritems():
      test_name = 'full_%s_%s' % (_sanitize_nonalpha(mastername),
                                  _sanitize_nonalpha(buildername))
      tests = []
      for (pass_first, suffix) in ((True, '_pass'), (False, '_fail')):
        test = (
          properties(mastername, buildername) +
          api.platform(
              bot_config['testing']['platform'],
              bot_config.get(
                  'chromium_config_kwargs', {}).get('TARGET_BITS', 64)) +
          api.test(test_name + suffix) +
          api.override_step_data(with_patch, canned_test(passing=pass_first))
        )
        if not pass_first:
          test += api.override_step_data(
              without_patch, canned_test(passing=False, minimal=True))
        tests.append(test)

      for test in tests:
        yield test

  # This tests that if the first fails, but the second pass succeeds
  # that we fail the whole build.
  yield (
    api.test('minimal_pass_continues') +
    properties('client.v8.fyi', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch, canned_test(passing=False)) +
    api.override_step_data(without_patch,
                           canned_test(passing=True, minimal=True))
  )


  # This tests what happens if something goes horribly wrong in
  # run_web_tests.py and we return an internal error; the step should
  # be considered a hard failure and we shouldn't try to compare the
  # lists of failing tests.
  # 255 == test_run_results.UNEXPECTED_ERROR_EXIT_STATUS in run_web_tests.py.
  yield (
    api.test('blink_web_tests_unexpected_error') +
    properties('client.v8.fyi', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch, canned_test(passing=False, retcode=255))
  )

  # TODO(dpranke): crbug.com/357866 . This tests what happens if we exceed the
  # number of failures specified with --exit-after-n-crashes-or-times or
  # --exit-after-n-failures; the step should be considered a hard failure and
  # we shouldn't try to compare the lists of failing tests.
  # 130 == test_run_results.INTERRUPTED_EXIT_STATUS in run_web_tests.py.
  yield (
    api.test('blink_web_tests_interrupted') +
    properties('client.v8.fyi', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch, canned_test(passing=False, retcode=130))
  )

  # This tests what happens if we don't trip the thresholds listed
  # above, but fail more tests than we can safely fit in a return code.
  # (this should be a soft failure and we can still retry w/o the patch
  # and compare the lists of failing tests).
  yield (
    api.test('too_many_failures_for_retcode') +
    properties('client.v8.fyi', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch,
                           canned_test(passing=False,
                                       num_additional_failures=125)) +
    api.override_step_data(without_patch,
                           canned_test(passing=True, minimal=True))
  )

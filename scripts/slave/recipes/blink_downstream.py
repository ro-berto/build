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
  'build/isolate',
  'build/swarming',
  'build/test_utils',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/buildbucket',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
]


def V8Builder(config, bits, platform, swarming_shards, swarming_priority=35):
  return {
    'gclient_apply_config': ['show_v8_revision'],
    'chromium_apply_config': [],
    'chromium_config_kwargs': {
      'BUILD_CONFIG': config,
      'TARGET_BITS': bits,
    },
    'swarming_shards': swarming_shards,
    'swarming_priority': swarming_priority,
    'testing': {'platform': platform},
  }


BUILDERS = freeze({
  'client.v8.fyi': {
    'builders': {
      'V8-Blink Win':
          V8Builder('Release', 32, 'win', swarming_shards=8),
      'V8-Blink Mac':
          V8Builder('Release', 64, 'mac', swarming_shards=8),
      # Use CI-priority on this bot because it's blocking V8's lkgr.
      'V8-Blink Linux 64':
          V8Builder('Release', 64, 'linux', swarming_shards=6,
                    swarming_priority=25),
      'V8-Blink Linux 64 - future':
          V8Builder('Release', 64, 'linux', swarming_shards=6),
      'V8-Blink Linux 64 (dbg)':
          V8Builder('Debug', 64, 'linux', swarming_shards=10),
    },
  },
})


OS_MAPPING = {
  'linux': 'Ubuntu-14.04',
  'win': 'Windows-7-SP1',
  'mac': 'Mac-10.13',
}


def build(api, suffix):
  """Compiles and isolates the checked-out code.

  Args:
    api: Recipe module api.
    suffix: Step name suffix to disambiguate repeated calls.
  """
  api.chromium_tests.run_mb_and_compile(
      ['blink_tests'], ['webkit_layout_tests_exparchive'],
      name_suffix=suffix,
  )

  api.isolate.isolate_tests(
          api.chromium.output_dir,
          suffix=suffix,
          targets=['webkit_layout_tests_exparchive'],
          verbose=True)


class DetermineFailuresTool(object):
  """Utility class allowing to run tests in two settings. Failing tests will be
  compared to a baseline run. If also failing there, they will be ignored.
  """
  def __init__(self, api, bot_update_result):
    self.api = api
    self.bot_update_result = bot_update_result

  @property
  def test_args(self):
    return [
      '--num-retries=3',
      '--additional-expectations',
      str(self.api.path['checkout'].join(
          'v8', 'tools', 'blink_tests', 'TestExpectations')),
    ] + (['--debug'] if self.api.chromium.c.build_config_fs == 'Debug' else [])

  def set_baseline(self, failing_test):
    """Expected to reset the testing environment into a baseline state after
    test failures.

    After tests have run and some have failed in the configured environment
    (e.g. with patch), this method is expected to change the testing
    environment to a baseline state to compare to (e.g. without patch).

    Args:
      failing_test: Blink test object representing the failing test of the first
      run.
    """
    raise NotImplementedError()  # pragma: no cover

  def determine_new_failures(self, num_shards):
    test = self.api.chromium_tests.steps.SwarmingIsolatedScriptTest(
        name='webkit_layout_tests',
        args=self.test_args,
        target_name='webkit_layout_tests_exparchive',
        shards=num_shards,
        merge={
          'args': ['--verbose'],
          'script': self.api.path['checkout'].join(
              'third_party', 'blink', 'tools', 'merge_web_test_results.py'),
        },
        results_handler=self.api.chromium_tests.steps.LayoutTestResultsHandler()
    )

    # Since we don't implement 'retry with patch', we set the corresponding
    # flag on the Test instances.
    # TODO(machenbach): Maybe we should keep this activated to make the
    # builders more reliable.
    test._should_retry_with_patch = False

    failing_tests = self.api.test_utils.run_tests_with_patch(self.api, [test])

    if not failing_tests:
      return

    # We only run layout tests, so there's only one instance of tests.
    assert len(failing_tests) == 1

    try:
      self.set_baseline(failing_tests[0])
      self.api.test_utils.run_tests(self.api, failing_tests, 'without patch')
    finally:
      success = self.api.test_utils.summarize_test_with_patch_deapplied(
          self.api, failing_tests[0])
      if not success:
        raise self.api.step.StepFailure(failing_tests[0].name + ' failed.')



class DetermineFutureFailuresTool(DetermineFailuresTool):
  """Utility class for running tests with V8's future staging flag passed, and
  retrying failing tests without the flag.
  """
  @property
  def test_args(self):
    return super(DetermineFutureFailuresTool, self).test_args + [
      '--additional-expectations',
      str(self.api.path['checkout'].join(
          'v8', 'tools', 'blink_tests', 'TestExpectationsFuture')),
      '--additional-driver-flag',
      '--js-flags=--future',
    ]

  def set_baseline(self, failing_test):
    # HACK(machenbach): SwarmingIsolatedScriptTest stores state about failing
    # tests. In order to rerun without future, we need to remove the extra args
    # from the existing test object.
    failing_test._args = super(DetermineFutureFailuresTool, self).test_args


class DetermineToTFailuresTool(DetermineFailuresTool):
  """Utility class for running tests with a patch applied, and retrying
  failing tests without the patch.
  """
  def set_baseline(self, failing_test):
    bot_update_json = self.bot_update_result.json.output
    self.api.gclient.c.revisions['src'] = str(
        bot_update_json['properties']['got_cr_revision'])
    # Reset component revision to the pinned revision from chromium's DEPS
    # for comparison.
    del self.api.gclient.c.revisions['src/v8']
    # Update without changing got_revision. The first sync is the revision
    # that is tested. The second is just for comparison. Setting got_revision
    # again confuses the waterfall's console view.
    self.api.bot_update.ensure_checkout(
        ignore_input_commit=True, update_presentation=False)

    build(self.api, ' (without patch)')


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

  # Set up swarming.
  api.swarming.default_priority = bot_config['swarming_priority']
  api.swarming.set_default_dimension('gpu', 'none')
  api.swarming.set_default_dimension('os', OS_MAPPING[api.platform.name])
  api.swarming.set_default_dimension('pool', 'Chrome')
  api.swarming.add_default_tag('project:v8')
  api.swarming.add_default_tag('purpose:CI')
  api.swarming.add_default_tag('purpose:luci')
  api.swarming.add_default_tag('purpose:post-commit')

  # Sync component to current component revision.
  component_revision = api.buildbucket.gitiles_commit.id or 'HEAD'
  api.gclient.c.revisions['src/v8'] = component_revision

  # Ensure we remember the chromium revision.
  api.gclient.c.got_revision_reverse_mapping['got_cr_revision'] = 'src'
  api.gclient.c.got_revision_mapping.pop('src', None)

  # Run all steps in the checkout dir (consistent with chromium_tests).
  with api.context(cwd=api.chromium_checkout.get_checkout_dir(bot_config)):
    step_result = api.bot_update.ensure_checkout()

    api.chromium.ensure_goma()

    with api.context(cwd=api.path['checkout']):
      api.chromium.runhooks()

    build(api, ' (with patch)')

    new_failures_tool_cls = DetermineToTFailuresTool
    if 'future' in buildername:
      new_failures_tool_cls = DetermineFutureFailuresTool

    # Test with and without baseline to determine new failures. We use
    # chromium_tests.m instead of api to get correct recipe module
    # dependencies for using raw classes from chromium_tests.steps.
    new_failures_tool_cls(
        api.chromium_tests.m, step_result).determine_new_failures(
            num_shards=bot_config['swarming_shards'])


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  canned_test = api.test_utils.canned_isolated_script_output
  with_patch = 'webkit_layout_tests (with patch)'
  without_patch = 'webkit_layout_tests (without patch)'

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
            api.override_step_data(with_patch, canned_test(
                passing=pass_first, isolated_script_passing=pass_first))
        )
        if not pass_first:
          test += api.override_step_data(without_patch, canned_test(
              passing=False, isolated_script_passing=False))
        tests.append(test)

      for test in tests:
        yield test

  # This tests that if the first fails, but the second pass succeeds
  # that we fail the whole build.
  yield (
    api.test('minimal_pass_continues') +
    properties('client.v8.fyi', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch, canned_test(
        passing=False, isolated_script_passing=False)) +
    api.override_step_data(without_patch, canned_test(
        passing=True, isolated_script_passing=True))
  )

  # This tests what happens if something goes horribly wrong in
  # run_web_tests.py and we return an internal error; the step should
  # be considered a hard failure and we shouldn't try to compare the
  # lists of failing tests.
  # 255 == test_run_results.UNEXPECTED_ERROR_EXIT_STATUS in run_web_tests.py.
  yield (
    api.test('blink_web_tests_unexpected_error') +
    properties('client.v8.fyi', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch, canned_test(
        passing=False,
        isolated_script_passing=False,
        isolated_script_retcode=255))
  )

  # TODO(dpranke): crbug.com/357866 . This tests what happens if we exceed the
  # number of failures specified with --exit-after-n-crashes-or-times or
  # --exit-after-n-failures; the step should be considered a hard failure and
  # we shouldn't try to compare the lists of failing tests.
  # 130 == test_run_results.INTERRUPTED_EXIT_STATUS in run_web_tests.py.
  yield (
    api.test('blink_web_tests_interrupted') +
    properties('client.v8.fyi', 'V8-Blink Linux 64') +
    api.override_step_data(with_patch, canned_test(
        passing=False,
        isolated_script_passing=False,
        isolated_script_retcode=130))
  )

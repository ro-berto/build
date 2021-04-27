# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'recipe_engine/properties',
    'test_utils',
]


def RunSteps(api):
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  with api.chromium.chromium_layout():
    return api.chromium_tests.integration_steps(builder_id, builder_config)


def GenTests(api):

  def ci_props(builder_group='chromium.linux',
               builder='Linux Builder',
               extra_swarmed_tests=None):
    swarm_hashes = {}
    if extra_swarmed_tests:
      for test in extra_swarmed_tests:
        swarm_hashes[test] = '[dummy hash for %s]' % test

    return sum([
        api.properties(swarm_hashes=swarm_hashes),
        api.chromium_tests_builder_config.ci_build(
            project='project',
            builder_group=builder_group,
            builder=builder,
            git_repo='https://chromium.googlesource.com/v8/v8.git',
        ),
    ], api.empty_test_data())

  def blink_test_setup():
    return (
      ci_props(extra_swarmed_tests=['blink_web_tests']) +
      api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
          'Linux Builder': {
            'isolated_scripts': [
              {
                'isolate_name': 'blink_web_tests',
                'name': 'blink_web_tests',
                'swarming': {'can_use_on_swarming_builders': True},
                'results_handler': 'layout tests',
              },
            ],
          },
        }
      )
    )

  def blink_test(
      succeeds_with_patch,
      succeeds_retry_with_patch=None,
      succeeds_without_patch=None):
    if succeeds_without_patch is not None:
      assert succeeds_retry_with_patch is not None

    def test_result(is_successful):
      return api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=is_successful, swarming=True,
                  isolated_script_passing=is_successful,
                  isolated_script_retcode=0 if is_successful else 125),
              failure=not is_successful)

    result = blink_test_setup()

    result += api.override_step_data(
        'blink_web_tests (with patch)',
        test_result(succeeds_with_patch))

    if succeeds_retry_with_patch is not None:
      result += api.override_step_data(
          'blink_web_tests (retry shards with patch)',
          test_result(succeeds_retry_with_patch))

      if succeeds_without_patch is not None:
        result += api.override_step_data(
            'blink_web_tests (without patch)',
            test_result(succeeds_without_patch))

    return result

  yield api.test(
      'bug_introduced_by_commit',
      blink_test(
          succeeds_with_patch=False,
          succeeds_retry_with_patch=False,
          succeeds_without_patch=True),
      api.post_process(post_process.MustRun, 'blink_web_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'blink_web_tests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'blink_web_tests (without patch)'),
      api.post_process(post_process.StatusFailure),
  )

  yield api.test(
      'bug_introduced_by_chromium',
      blink_test(
          succeeds_with_patch=False,
          succeeds_retry_with_patch=False,
          succeeds_without_patch=False),
      api.post_process(post_process.MustRun, 'blink_web_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'blink_web_tests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'blink_web_tests (without patch)'),
      api.post_process(post_process.StatusSuccess),
  )

  yield api.test(
      'flaky_test',
      blink_test(succeeds_with_patch=False, succeeds_retry_with_patch=True),
      api.post_process(post_process.MustRun, 'blink_web_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'blink_web_tests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'blink_web_tests (without patch)'),
      api.post_process(post_process.StatusSuccess),
  )

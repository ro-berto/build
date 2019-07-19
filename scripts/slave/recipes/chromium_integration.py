# Copyright 2019 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
  'chromium',
  'chromium_swarming',
  'chromium_tests',
  'recipe_engine/buildbucket',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'test_utils',
]


def RunSteps(api):
  with api.chromium.chromium_layout():
    return api.chromium_tests.integration_steps()

def GenTests(api):
  def ci_props(config='Release', mastername='chromium.linux',
               builder='Linux Builder',
               extra_swarmed_tests=None, **kwargs):
    kwargs.setdefault('path_config', 'kitchen')
    swarm_hashes = {}
    if extra_swarmed_tests:
      for test in extra_swarmed_tests:
        swarm_hashes[test] = '[dummy hash for %s]' % test

    return (
      api.properties.generic(
        build_config=config,
        mastername=mastername,
        swarm_hashes=swarm_hashes,
        **kwargs
      ) +
      api.buildbucket.ci_build(
        builder=builder,
        git_repo='https://chromium.googlesource.com/v8/v8.git',
      ) +
      api.runtime(
        is_luci=True,
        is_experimental=False
      )
    )

  def blink_test_setup():
    return (
      ci_props(extra_swarmed_tests=['blink_web_tests']) +
      api.platform.name('linux') +
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

  yield (
    api.test('bug_introduced_by_commit') +
    blink_test(
        succeeds_with_patch=False,
        succeeds_retry_with_patch=False,
        succeeds_without_patch=True) +
    api.post_process(post_process.MustRun, 'blink_web_tests (with patch)') +
    api.post_process(
        post_process.MustRun, 'blink_web_tests (retry shards with patch)') +
    api.post_process(post_process.MustRun, 'blink_web_tests (without patch)') +
    api.post_process(post_process.StatusFailure) +
    api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('bug_introduced_by_chromium') +
    blink_test(
        succeeds_with_patch=False,
        succeeds_retry_with_patch=False,
        succeeds_without_patch=False) +
    api.post_process(
        post_process.MustRun, 'blink_web_tests (with patch)') +
    api.post_process(
        post_process.MustRun, 'blink_web_tests (retry shards with patch)') +
    api.post_process(post_process.MustRun, 'blink_web_tests (without patch)') +
    api.post_process(post_process.StatusSuccess) +
    api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('flaky_test') +
    blink_test(
        succeeds_with_patch=False,
        succeeds_retry_with_patch=True) +
    api.post_process(post_process.MustRun, 'blink_web_tests (with patch)') +
    api.post_process(
      post_process.MustRun, 'blink_web_tests (retry shards with patch)') +
    api.post_process(
      post_process.DoesNotRun, 'blink_web_tests (without patch)') +
    api.post_process(post_process.StatusSuccess) +
    api.post_process(post_process.DropExpectation)
  )

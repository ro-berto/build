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
    kwargs.setdefault('path_config', 'generic')
    swarm_hashes = {}
    if extra_swarmed_tests:
      for test in extra_swarmed_tests:
        swarm_hashes[test] = '[dummy hash for %s]' % test

    return sum([
        api.chromium.ci_build(
            mastername=mastername,
            builder=builder,
            git_repo='https://chromium.googlesource.com/v8/v8.git',
        ),
        api.properties(
            build_config=config, swarm_hashes=swarm_hashes, **kwargs),
        api.runtime(is_luci=True, is_experimental=False),
    ], api.empty_test_data())

  yield api.test(
      'deapply_deps_after_failure',
      ci_props(extra_swarmed_tests=['blink_web_tests']),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Builder': {
                  'isolated_scripts': [{
                      'isolate_name': 'blink_web_tests',
                      'name': 'blink_web_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                      'results_handler': 'layout tests',
                  },],
              },
          }),
      api.override_step_data(
          'blink_web_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  swarming=True,
                  isolated_script_passing=False,
                  isolated_script_retcode=125),
              failure=True)),
      api.override_step_data(
          'blink_web_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  swarming=True,
                  isolated_script_passing=False,
                  isolated_script_retcode=125),
              failure=True)),
      api.override_step_data(
          'blink_web_tests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True, swarming=True, isolated_script_passing=True))),
      api.post_process(post_process.MustRun, 'blink_web_tests (with patch)'),
      api.post_process(post_process.MustRun,
                       'blink_web_tests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'blink_web_tests (without patch)'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

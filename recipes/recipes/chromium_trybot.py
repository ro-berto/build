# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import (Filter, DoesNotRun, DropExpectation,
                                        StatusFailure, StatusSuccess)

DEPS = [
  'build',
  'chromium',
  'chromium_android',
  'chromium_checkout',
  'chromium_swarming',
  'chromium_tests',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gerrit',
  'depot_tools/tryserver',
  'filter',
  'isolate',
  'recipe_engine/buildbucket',
  'recipe_engine/commit_position',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/legacy_annotation',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'recipe_engine/runtime',
  'test_results',
  'test_utils',
]


def RunSteps(api):
  with api.chromium.chromium_layout():
    return api.chromium_tests.trybot_steps()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  canned_test = api.test_utils.canned_gtest_output

  def swarm_hashes(swarm_hashes=None, extra_swarmed_tests=None):
    swarm_hashes = dict(swarm_hashes or {})
    for test in extra_swarmed_tests or []:
      swarm_hashes[test] = '[dummy hash for %s]' % test
    return api.properties(swarm_hashes=swarm_hashes)

  def base_unittests_additional_compile_target():
    return api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'gtest_tests': ['base_unittests'],
            },
        }
    )

  # Regression test for http://crbug.com/453471#c16
  yield api.test(
      'clobber_analyze',
      api.chromium.try_build(builder='linux_chromium_clobber_rel_ng'),
      api.platform.name('linux'),
      api.override_step_data(
          'analyze',
          api.json.output({
              'status': 'Found dependency',
              'test_targets': [],
              'compile_targets': ['base_unittests', 'net_unittests']
          })),
  )

  # Do not fail the build if process_dumps fails.
  # http://crbug.com/520660
  yield api.test(
      'process_dumps_failure',
      api.chromium.try_build(
          builder_group='tryserver.chromium.win', builder='win7-rel'),
      api.platform.name('win'),
      api.chromium_tests.read_source_side_spec('chromium.win', {
          'Win7 Tests (1)': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.filter.suppress_analyze(),
      api.override_step_data('base_unittests (with patch)',
                             canned_test(passing=True, legacy_annotation=True)),
      api.override_step_data('process_dumps',
                             api.legacy_annotation.failure_step),
  )

  yield api.test(
      'invalid_results',
      api.chromium.try_build(),
      api.platform.name('linux'),
      base_unittests_additional_compile_target(),
      api.filter.suppress_analyze(),
      api.override_step_data('base_unittests (with patch)',
                             canned_test(passing=False,
                                         legacy_annotation=True)),
      api.override_step_data('base_unittests (without patch)',
                             api.legacy_annotation.failure_step),
  )

  yield api.test(
      'script_test_with_overridden_compile_targets',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'scripts': [{
                      'name': 'script_test',
                      'script': 'fake_script.py',
                      'override_compile_targets': ['overridden_target']
                  }],
              }
          }),
  )

  yield api.test(
      'dynamic_isolated_script_test_on_trybot_passing',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['telemetry_gpu_unittests']),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.filter.suppress_analyze(),
      api.override_step_data(
          'telemetry_gpu_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True, is_win=False, swarming=True))),
  )

  yield api.test(
      'dynamic_isolated_script_test_on_trybot_failing',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['telemetry_gpu_unittests']),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.filter.suppress_analyze(),
      api.override_step_data(
          'telemetry_gpu_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  is_win=False,
                  swarming=True,
                  isolated_script_passing=False,
              ),
              failure=True)),
      api.override_step_data(
          'telemetry_gpu_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=False,
                  is_win=False,
                  swarming=True,
                  isolated_script_passing=False,
              ),
              failure=True)),
      api.override_step_data(
          'telemetry_gpu_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
                  isolated_script_passing=True,
              ))),
  )

  yield api.test(
      'dynamic_isolated_script_test_with_args_on_trybot',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['telemetry_gpu_unittests']),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'args': ['--correct-common-arg'],
                      'non_precommit_args':
                          ['--SHOULD-NOT-BE-PRESENT-DURING-THE-RUN'],
                      'precommit_args': [
                          '--these-args-should-be-present',
                          '--test-machine-name=\"${buildername}\"',
                          '--build-revision=\"${got_revision}\"',
                      ],
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.filter.suppress_analyze(),
      api.override_step_data(
          'telemetry_gpu_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
              ),
              failure=False)),
  )

  yield api.test(
      'dynamic_swarmed_isolated_script_test_failure_no_result_json',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['telemetry_gpu_unittests']),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.filter.suppress_analyze(),
      api.override_step_data(
          'telemetry_gpu_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.json.output({}), failure=True, retcode=1)),
  )

  yield api.test(
      'swarming_test_with_priority_expiration_and_timeout',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['gl_tests']),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                          'expiration': 7200,
                          'hard_timeout': 1800,
                      },
                  },],
              },
          }),
      api.filter.suppress_analyze(),
  )

  yield api.test(
      'swarming_trigger_failure',
      api.chromium.try_build(),
      # Specifying empty swarm hashes will override the value of
      # isolate.isolated_tests so that when we attempt to run base_unittests
      # we get an error
      swarm_hashes(),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.filter.suppress_analyze(),
  )

  yield api.test(
      'swarming_test_failure',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['gl_tests']),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.filter.suppress_analyze(),
      api.override_step_data(
          'gl_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              canned_test(passing=False), failure=True)),
  )

  yield api.test(
      'swarming_test_failure_no_patch_deapplication',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['gl_tests']),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'test': 'gl_tests',
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                  },],
              },
          }),
      api.filter.suppress_analyze(),
      api.override_step_data(
          'gl_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              canned_test(passing=False), failure=True)),
      api.override_step_data(
          'gl_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              canned_test(passing=False), failure=True)),
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('foo.cc\ntesting/buildbot/bar.json')),
      api.post_process(StatusFailure),
      api.post_process(DropExpectation),
  )

  yield api.test(
      'compile_failure_without_patch_deapply_fn',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.filter.suppress_analyze(),
      api.override_step_data('base_unittests (with patch)',
                             canned_test(passing=False,
                                         legacy_annotation=True)),
      api.step_data('compile (without patch)',
                    api.legacy_annotation.infra_failure_step),
  )

  yield api.test(
      'compile_failure_infra',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.filter.suppress_analyze(),
      api.override_step_data('compile (with patch)', retcode=1),
      api.step_data(
          'postprocess_for_goma.goma_jsonstatus',
          api.json.output(data={
              'notice': [{
                  'infra_status': {
                      'ping_status_code': 408,
                  },
              },],
          })),
  )

  for step in ('bot_update', 'gclient runhooks (with patch)'):
    yield api.test(
        _sanitize_nonalpha(step) + '_failure',
        api.chromium.try_build(),
        api.platform.name('linux'),
        api.step_data(step, retcode=1),
    )

  yield api.test(
      'runhooks_failure',
      api.chromium.try_build(
          builder='win7-rel', builder_group='tryserver.chromium.win'),
      api.platform.name('win'),
      api.step_data('gclient runhooks (with patch)', retcode=1),
      api.step_data('gclient runhooks (without patch)', retcode=1),
  )

  yield api.test(
      'runhooks_failure_ng',
      api.platform('linux', 64),
      api.chromium.try_build(),
      api.step_data('gclient runhooks (with patch)', retcode=1),
  )

  yield api.test(
      'compile_failure_ng',
      api.platform('linux', 64),
      api.chromium.try_build(),
      api.filter.suppress_analyze(),
      base_unittests_additional_compile_target(),
      api.step_data('compile (with patch)', retcode=1),
  )

  # Test that the component rev for v8 is correctly applied
  # both on the initial checkout and after deapplying the patch.
  yield api.test(
      'compile_failure_with_component_rev',
      api.chromium.try_build(
          project='v8',
          builder_group='tryserver.v8',
          builder='v8_linux_chromium_gn_rel',
          git_repo='https://chromium.googlesource.com/v8/v8',
      ),
      api.platform('linux', 64),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'V8 Linux GN': {
              'additional_compile_targets': ['base_unittests'],
          },
      }),
      api.filter.suppress_analyze(['v8/f.*']),
      api.step_data('compile (with patch)', retcode=1),
  )

  yield api.test(
      'compile_failure_without_patch_ng',
      api.platform('linux', 64),
      api.chromium.try_build(),
      api.filter.suppress_analyze(),
      base_unittests_additional_compile_target(),
      api.step_data('compile (with patch)', retcode=1),
  )

  yield api.test(
      'check_swarming_version_failure',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.step_data('swarming.py --version', retcode=1),
  )

  # Successfully compiling, isolating and running two targets on swarming for a
  # commit queue job.
  yield api.test(
      'swarming_basic_cq',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['base_unittests', 'browser_tests']),
      api.platform.name('linux'),
      api.filter.suppress_analyze(),
  )

  # Successfully compiling, isolating and running two targets on swarming for a
  # manual try job.
  yield api.test(
      'swarming_basic_try_job',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['base_unittests', 'browser_tests']),
      api.platform.name('linux'),
      api.filter.suppress_analyze(),
  )

  # One target (browser_tests) failed to produce *.isolated file.
  yield api.test(
      'swarming_missing_isolated',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['base_unittests']),
      api.platform.name('linux'),
      api.filter.suppress_analyze(),
  )

  # Does not result in a compile
  yield api.test(
      'no_compile_because_of_analyze',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {}),
      api.post_process(DoesNotRun, 'compile (with patch)'),
      api.post_process(Filter('analyze')),
  )

  # This should result in a compile.
  yield api.test(
      'compile_because_of_analyze_matching_exclusion',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {}),
      api.filter.suppress_analyze(),
      base_unittests_additional_compile_target(),
      api.post_process(
          Filter('analyze', 'analyze_matched_exclusion',
                 'compile (with patch)')),
  )

  # This should result in a compile.
  yield api.test(
      'compile_because_of_analyze',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {}),
      api.override_step_data(
          'analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['browser_tests'],
              'test_targets': []
          })),
      api.post_process(Filter('analyze', 'compile (with patch)')),
  )

  # Tests compile_targets portion of analyze module with filtered tests
  yield api.test(
      'compile_because_of_analyze_with_filtered_tests',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.override_step_data(
          'analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['browser_tests', 'base_unittests'],
              'test_targets': ['browser_tests', 'base_unittests']
          })),
      api.post_process(Filter('analyze', 'compile (with patch)')),
  )

  # Tests compile_target portion of analyze module with filtered compile targets
  yield api.test(
      'compile_because_of_analyze_with_filtered_compile_targets',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.override_step_data(
          'analyze',
          api.json.output({
              'status': 'Found dependency',
              'test_targets': ['browser_tests', 'base_unittests'],
              'compile_targets': ['chrome', 'browser_tests', 'base_unittests']
          })),
      api.post_process(Filter('analyze', 'compile (with patch)')),
  )

  # Tests compile_targets portion of analyze with a bot that doesn't include the
  # 'all' target.
  yield api.test(
      'compile_because_of_analyze_with_filtered_compile_targets_exclude_all',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.override_step_data(
          'analyze',
          api.json.output({
              'status': 'Found dependency',
              'test_targets': ['browser_tests', 'base_unittests'],
              'compile_targets': ['base_unittests']
          })),
      api.post_process(Filter('analyze', 'compile (with patch)')),
  )

  # Tests compile_targets portion of analyze with a bot that doesn't include the
  # 'all' target.
  yield api.test(
      'analyze_finds_invalid_target',
      api.chromium.try_build(),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.override_step_data(
          'analyze',
          api.json.output(
              {'invalid_targets': ['invalid target', 'another one']})),
      api.post_process(Filter('analyze', '$result')),
      api.post_process(StatusFailure),
  )

  yield api.test(
      'use_v8_patch_on_chromium_trybot',
      api.chromium.try_build(
          builder='win7-rel',
          builder_group='tryserver.chromium.win',
          git_repo='https://chromium.googlesource.com/v8/v8',
      ),
      api.platform.name('win'),
  )

  yield api.test(
      'chromium_trybot_gerrit_feature_branch',
      api.platform('linux', 64),
      api.chromium.try_build(),
      api.filter.suppress_analyze(),
      base_unittests_additional_compile_target(),
      api.step_data('compile (with patch)', retcode=1),
      api.tryserver.gerrit_change_target_ref('refs/heads/experimental/feature'),
      api.post_process(Filter('gerrit fetch current CL info', 'bot_update')),
  )

  yield api.test(
      'use_webrtc_patch_on_chromium_trybot',
      api.chromium.try_build(git_repo='https://webrtc.googlesource.com/src'),
      api.platform.name('linux'),
  )

  yield api.test(
      'use_webrtc_patch_on_chromium_trybot_compile_failure',
      api.chromium.try_build(git_repo='https://webrtc.googlesource.com/src'),
      api.platform.name('linux'),
      base_unittests_additional_compile_target(),
      api.filter.suppress_analyze(more_exclusions=['third_party/webrtc/f.*']),
      api.step_data('compile (with patch)', retcode=1),
  )

  yield api.test(
      'use_skia_patch_on_chromium_trybot',
      api.chromium.try_build(
          builder='win7-rel',
          builder_group='tryserver.chromium.win',
          git_repo='https://skia.googlesource.com/skia'),
      api.platform.name('win'),
  )

  swarmed_webkit_tests = sum([
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=['blink_web_tests']),
      api.platform.name('linux'),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'isolated_scripts': [{
                      'isolate_name': 'blink_web_tests',
                      'name': 'blink_web_tests',
                      'resultdb': {
                          'enable': True
                      },
                      'swarming': {
                          'can_use_on_swarming_builders': True
                      },
                      'results_handler': 'layout tests',
                  },],
              },
          }),
      api.filter.suppress_analyze(),
  ], api.empty_test_data())

  # This tests what happens if something goes horribly wrong in
  # run_web_tests.py and we return an internal error; the step should
  # be considered a hard failure and we shouldn't try to compare the
  # lists of failing tests.
  # 255 == test_run_results.UNEXPECTED_ERROR_EXIT_STATUS in run_web_tests.py.
  yield api.test(
      'swarmed_webkit_tests_unexpected_error',
      swarmed_webkit_tests,
      api.override_step_data(
          'blink_web_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
                  isolated_script_passing=False,
                  isolated_script_retcode=255),
              failure=True)),
  )

  # TODO(dpranke): crbug.com/357866 . This tests what happens if we exceed the
  # number of failures specified with --exit-after-n-crashes-or-times or
  # --exit-after-n-failures; the step should be considered a hard failure and
  # we shouldn't try to compare the lists of failing tests.
  # 130 == test_run_results.INTERRUPTED_EXIT_STATUS in run_web_tests.py.
  yield api.test(
      'swarmed_webkit_tests_interrupted',
      swarmed_webkit_tests,
      api.override_step_data(
          'blink_web_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
                  isolated_script_passing=False,
                  isolated_script_retcode=130),
              failure=True)),
  )

  # This tests what happens if we don't trip the thresholds listed
  # above, but fail more tests than we can safely fit in a return code.
  # (this should be a soft failure and we can still retry w/o the patch
  # and compare the lists of failing tests).
  yield api.test(
      'swarmed_layout_tests_too_many_failures_for_retcode',
      swarmed_webkit_tests,
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
                  passing=True, isolated_script_passing=True))),
  )

  yield api.test(
      'use_skia_patch_on_blink_trybot',
      api.chromium.try_build(
          builder_group='tryserver.blink',
          builder='mac10.12-blink-rel',
          git_repo='https://skia.googlesource.com/skia'),
      api.platform.name('mac'),
  )

  yield api.test(
      'use_v8_patch_on_blink_trybot',
      api.chromium.try_build(
          builder_group='tryserver.blink',
          builder='mac10.12-blink-rel',
          git_repo='https://chromium.googlesource.com/v8/v8'),
      api.platform.name('mac'),
  )


  def check_ordering(check, step_odict, *steps):
    test_steps = [
        'test_pre_run (with patch).[trigger] 10_gtest (with patch)',
        'test_pre_run (with patch).[trigger] 6_isolated_tests (with patch)',
        'test_pre_run (with patch).[trigger] 5_gtest (with patch)',
        'test_pre_run (with patch).[trigger] 3_isolated_tests (with patch)',
        'test_pre_run (with patch).[trigger] 2_isolated_tests (with patch)',
        'test_pre_run (with patch).[trigger] 1_gtest (with patch)',
    ]

    for step_name in step_odict:
      if not test_steps:
        break
      if test_steps[0] == step_name:
        test_steps.pop(0)

    check(not test_steps)


  # This test is used to confirm the order of test_pre_run.
  # Test having larger shards should be triggered faster than test with smaller
  # shards.
  yield api.test(
      'sorted',
      api.chromium.try_build(),
      swarm_hashes(extra_swarmed_tests=[
          '1_gtest', '2_isolated_tests', '3_isolated_tests', '5_gtest',
          '6_isolated_tests', '10_gtest'
      ]),
      api.platform.name('linux'),
      api.override_step_data(
          'read test spec (chromium.linux.json)',
          api.json.output({
              'Linux Tests': {
                  'gtest_tests': [
                      {
                          'name': '10_gtest',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 10,
                          },
                      },
                      {
                          'name': '1_gtest',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 1,
                          },
                      },
                      {
                          'name': '5_gtest',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 5,
                          },
                      },
                  ],
                  'isolated_scripts': [
                      {
                          'name': '3_isolated_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 3,
                          },
                      },
                      {
                          'name': '2_isolated_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 2,
                          },
                      },
                      {
                          'name': '6_isolated_tests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                              'shards': 6,
                          },
                      },
                  ],
              },
          })),
      api.filter.suppress_analyze(),
      api.post_process(check_ordering),
      api.post_process(DropExpectation),
  )

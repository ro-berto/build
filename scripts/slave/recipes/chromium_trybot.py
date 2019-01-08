# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.post_process import Filter, DropExpectation, StatusSuccess

DEPS = [
  'build',
  'chromium',
  'chromium_android',
  'chromium_checkout',
  'chromium_swarming',
  'chromium_tests',
  'commit_position',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/gerrit',
  'depot_tools/tryserver',
  'filter',
  'isolate',
  'recipe_engine/buildbucket',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'swarming',
  'test_results',
  'test_utils',
]


def RunSteps(api):
  # build/tests/masters_recipes_tests.py needs to manipulate the BUILDERS
  # dict, so we provide an API to dump it here.
  if api.properties.get('dump_builders'):  # pragma: no cover
    api.file.copy('Dump BUILDERS dict',
        api.json.input(api.chromium_tests.trybots),
        api.properties['dump_builders'])
    return

  with api.chromium.chromium_layout():
    return api.chromium_tests.trybot_steps()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  canned_test = api.test_utils.canned_gtest_output

  def props(config='Release', mastername='tryserver.chromium.linux',
            builder='linux_chromium_rel_ng',
            swarm_hashes=None, extra_swarmed_tests=None,
            **kwargs):
    bb_kwargs = {
        'project': 'chromium',
        'builder': builder,
    }

    kwargs.setdefault('path_config', 'kitchen')
    kwargs.setdefault('revision', None)
    kwargs.setdefault('bot_id', 'test_bot')
    if swarm_hashes is None:
      swarm_hashes = {}
    if extra_swarmed_tests:
      for test in extra_swarmed_tests:
        swarm_hashes[test] = '[dummy hash for %s]' % test
    return api.properties.tryserver(
      build_config=config,
      mastername=mastername,
      buildername=builder,
      swarm_hashes=swarm_hashes,
      **kwargs
    ) + api.buildbucket.try_build(**bb_kwargs)

  def suppress_analyze(more_exclusions=None):
    """Overrides analyze step data so that all targets get compiled."""
    return api.override_step_data(
        'read filter exclusion spec',
        api.json.output({
            'base': {
                'exclusions': ['f.*'] + (more_exclusions or []),
            },
            'chromium': {
                'exclusions': [],
            },
        })
    )

  def base_unittests_additional_compile_target():
    return api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'gtest_tests': ['base_unittests'],
            },
        }
    )

  # Regression test for http://crbug.com/453471#c16
  yield (
    api.test('clobber_analyze') +
    props(builder='linux_chromium_clobber_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data(
      'analyze',
      api.json.output({
          'status': 'Found dependency',
          'test_targets': [],
          'compile_targets': ['base_unittests', 'net_unittests']
      }))
  )

  # Do not fail the build if process_dumps fails.
  # http://crbug.com/520660
  yield (
    api.test('process_dumps_failure') +
    props(mastername='tryserver.chromium.win',
          builder='win7_chromium_rel_ng') +
    api.platform.name('win') +
    suppress_analyze() +
    api.override_step_data('process_dumps', retcode=1)
  )

  yield (
    api.test('invalid_results') +
    props() +
    api.platform.name('linux') +
    base_unittests_additional_compile_target() +
    suppress_analyze() +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('base_unittests (without patch)',
                           api.test_utils.gtest_results(None, retcode=1))
  )

  yield (
    api.test('script_test_with_overridden_compile_targets') +
    props() +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'scripts': [
                    {
                        'name': 'script_test',
                        'script': 'fake_script.py',
                        'override_compile_targets': ['overridden_target']
                    }
                ],
            }
        }
    )
  )

  yield (
    api.test('dynamic_isolated_script_test_on_trybot_passing') +
    props(extra_swarmed_tests=['telemetry_gpu_unittests']) +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        }
    ) +
    suppress_analyze() +
    api.override_step_data(
        'telemetry_gpu_unittests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True
        ) +
        api.swarming.canned_summary_output()
    )
  )

  yield (
    api.test('dynamic_isolated_script_test_on_trybot_failing') +
    props(extra_swarmed_tests=['telemetry_gpu_unittests']) +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        }
    ) +
    suppress_analyze() +
    api.override_step_data(
        'telemetry_gpu_unittests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True,
            isolated_script_passing=False,
        ) +
        api.swarming.canned_summary_output(failure=True),
    ) +
    api.override_step_data(
        'telemetry_gpu_unittests (without patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True,
            isolated_script_passing=True,
        ) +
        api.swarming.canned_summary_output()
    )
  )

  yield (
    api.test('dynamic_isolated_script_test_with_args_on_trybot') +
    props(extra_swarmed_tests=['telemetry_gpu_unittests']) +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'args': ['--correct-common-arg'],
                      'non_precommit_args': [
                        '--SHOULD-NOT-BE-PRESENT-DURING-THE-RUN'
                      ],
                      'precommit_args': [
                        '--these-args-should-be-present',
                        '--test-machine-name=\"${buildername}\"',
                        '--build-revision=\"${got_revision}\"',
                      ],
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        }
    ) +
    suppress_analyze() +
    api.override_step_data(
        'telemetry_gpu_unittests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True,
        ) +
        api.swarming.canned_summary_output(failure=False)
    )
  )

  yield (
    api.test(
        'dynamic_swarmed_isolated_script_test_failure_no_result_json') +
    props(extra_swarmed_tests=['telemetry_gpu_unittests']) +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        }
    ) +
    suppress_analyze() +
    api.override_step_data(
        'telemetry_gpu_unittests (with patch)',
        api.swarming.canned_summary_output(failure=True)
        + api.json.output({}),
        retcode=1)
  )

  yield (
    api.test('swarming_test_with_priority_expiration_and_timeout') +
    props(extra_swarmed_tests=['gl_tests']) +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'gtest_tests': [
                    {
                      'test': 'gl_tests',
                      'swarming': {
                        'can_use_on_swarming_builders': True,
                        'priority_adjustment': 'higher',
                        'expiration': 7200,
                        'hard_timeout': 1800,
                      },
                    },
                ],
            },
        }
    ) +
    suppress_analyze()
  )

  yield (
    api.test('swarming_trigger_failure') +
    props() +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'gtest_tests': [
                    {
                      'test': 'base_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        }
    ) +
    suppress_analyze()
  )

  yield (
    api.test('swarming_test_failure') +
    props(extra_swarmed_tests=['gl_tests']) +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'gtest_tests': [
                    {
                      'test': 'gl_tests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        }
    ) +
    suppress_analyze() +
    api.override_step_data(
        'gl_tests (with patch)',
        api.swarming.canned_summary_output(failure=True) +
        canned_test(passing=False))
  )

  yield (
    api.test('swarming_test_failure_no_patch_deapplication') +
    props(extra_swarmed_tests=['gl_tests']) +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'gtest_tests': [
                    {
                      'test': 'gl_tests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        }
    ) +
    suppress_analyze() +
    api.override_step_data(
        'gl_tests (with patch)',
        api.swarming.canned_summary_output(failure=True) +
        canned_test(passing=False)) +
    api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('foo.cc\ntesting/buildbot/bar.json')) +
    api.post_process(StatusSuccess) +
    api.post_process(Filter('gl_tests (retry with patch)'))
  )

  yield (
    api.test('compile_failure_without_patch_deapply_fn') +
    props() +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
              'gtest_tests': ['base_unittests'],
            },
        }
    ) +
    suppress_analyze() +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('compile (without patch)', retcode=1)
  )

  yield (
    api.test('compile_failure_infra') +
    props() +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
              'gtest_tests': ['base_unittests'],
            },
        }
    ) +
    suppress_analyze() +
    api.override_step_data(
        'compile (with patch)',
        retcode=1) +
    api.step_data(
        'postprocess_for_goma.goma_jsonstatus',
        api.json.output(
            data={
                'notice': [
                    {
                        'infra_status': {
                            'ping_status_code': 408,
                        },
                    },
                ],
            }))
  )

  for step in ('bot_update', 'gclient runhooks (with patch)'):
    yield (
      api.test(_sanitize_nonalpha(step) + '_failure') +
      props() +
      api.platform.name('linux') +
      api.step_data(step, retcode=1)
    )

  yield (
    api.test('runhooks_failure') +
    props(builder='win7_chromium_rel_ng',
          mastername='tryserver.chromium.win') +
    api.platform.name('win') +
    api.step_data('gclient runhooks (with patch)', retcode=1) +
    api.step_data('gclient runhooks (without patch)', retcode=1)
  )

  yield (
    api.test('runhooks_failure_ng') +
    api.platform('linux', 64) +
    props() +
    api.step_data('gclient runhooks (with patch)', retcode=1)
  )

  yield (
    api.test('compile_failure_ng') +
    api.platform('linux', 64) +
    props() +
    suppress_analyze() +
    base_unittests_additional_compile_target() +
    api.step_data('compile (with patch)', retcode=1)
  )

  # Test that the component rev for v8 is correctly applied
  # both on the initial checkout and after deapplying the patch.
  yield (
    api.test('compile_failure_with_component_rev') +
    api.platform('linux', 64) +
    props(mastername='tryserver.v8',
          builder='v8_linux_chromium_gn_rel') +
    api.properties(revision='a' * 40) +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'V8 Linux GN': {
                'additional_compile_targets': ['base_unittests'],
            },
        }
    ) +
    suppress_analyze() +
    api.step_data('compile (with patch)', retcode=1)
  )

  yield (
    api.test('compile_failure_without_patch_ng') +
    api.platform('linux', 64) +
    props() +
    suppress_analyze() +
    base_unittests_additional_compile_target() +
    api.step_data('compile (with patch)', retcode=1)
  )

  yield (
    api.test('check_swarming_version_failure') +
    props() +
    api.platform.name('linux') +
    api.step_data('swarming.py --version', retcode=1)
  )

  # Successfully compiling, isolating and running two targets on swarming for a
  # commit queue job.
  yield (
    api.test('swarming_basic_cq') +
    props(requester='commit-bot@chromium.org', blamelist=['joe@chromium.org'],
          extra_swarmed_tests=['base_unittests', 'browser_tests']) +
    api.platform.name('linux') +
    suppress_analyze()
  )

  # Successfully compiling, isolating and running two targets on swarming for a
  # manual try job.
  yield (
    api.test('swarming_basic_try_job') +
    props(requester='joe@chromium.org',
          extra_swarmed_tests=['base_unittests', 'browser_tests']) +
    api.platform.name('linux') +
    suppress_analyze()
  )

  # One target (browser_tests) failed to produce *.isolated file.
  yield (
    api.test('swarming_missing_isolated') +
    props(requester='commit-bot@chromium.org', blamelist=['joe@chromium.org'],
          extra_swarmed_tests=['base_unittests']) +
    api.platform.name('linux') +
    suppress_analyze()
  )

  yield (
    api.test('no_compile_because_of_analyze') +
    props() +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec('chromium.linux', {}))

  # This should result in a compile.
  yield (
    api.test('compile_because_of_analyze_matching_exclusion') +
    props() +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec('chromium.linux', {}) +
    suppress_analyze()
  )

  # This should result in a compile.
  yield (
    api.test('compile_because_of_analyze') +
    props() +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec('chromium.linux', {}) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'compile_targets': [],
                       'test_targets': []}))
  )

  yield (
    api.test('compile_because_of_analyze_with_filtered_tests_no_builder') +
    props() +
    api.platform.name('linux') +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'compile_targets': ['browser_tests', 'base_unittests'],
                       'test_targets': ['browser_tests', 'base_unittests']}))
  )

  yield (
    api.test('compile_because_of_analyze_with_filtered_tests') +
    props() +
    api.platform.name('linux') +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'compile_targets': ['browser_tests', 'base_unittests'],
                       'test_targets': ['browser_tests', 'base_unittests']}))
  )

  # Tests compile_target portion of analyze module.
  yield (
    api.test('compile_because_of_analyze_with_filtered_compile_targets') +
    props() +
    api.platform.name('linux') +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'test_targets': ['browser_tests', 'base_unittests'],
                       'compile_targets': ['chrome', 'browser_tests',
                                           'base_unittests']}))
  )

  # Tests compile_targets portion of analyze with a bot that doesn't include the
  # 'all' target.
  yield (
    api.test(
      'compile_because_of_analyze_with_filtered_compile_targets_exclude_all') +
    props() +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'gtest_tests': ['base_unittests'],
            },
        }
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'test_targets': ['browser_tests', 'base_unittests'],
                       'compile_targets': ['base_unittests']}))
  )

  # Tests compile_targets portion of analyze with a bot that doesn't include the
  # 'all' target.
  yield (
    api.test(
      'analyze_finds_invalid_target') +
    props() +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'gtest_tests': ['base_unittests'],
            },
        }
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'invalid_targets': ['invalid target', 'another one']}))
  )

  yield (
    api.test('use_v8_patch_on_chromium_trybot') +
    props(builder='win7_chromium_rel_ng',
          mastername='tryserver.chromium.win',
          repository='https://chromium.googlesource.com/v8/v8',
          patch_repository_url='https://chromium.googlesource.com/v8/v8',
          patch_project='v8') +
    api.platform.name('win')
  )

  yield (
    api.test('chromium_trybot_gerrit_feature_branch') +
    api.platform('linux', 64) +
    props() +
    suppress_analyze() +
    base_unittests_additional_compile_target() +
    api.step_data('compile (with patch)', retcode=1) +
    api.tryserver.gerrit_change_target_ref('refs/heads/experimental/feature') +
    api.post_process(
        Filter('gerrit fetch current CL info',
               'bot_update'))
  )

  yield (
    api.test('use_webrtc_patch_on_chromium_trybot') +
    props(
        repository='https://webrtc.googlesource.com/src',
        patch_repository_url='https://webrtc.googlesource.com/src',
        patch_project='webrtc') +
    api.platform.name('linux')
  )

  yield (
    api.test('use_webrtc_patch_on_chromium_trybot_compile_failure') +
    props(
        repository='https://webrtc.googlesource.com/src',
        patch_repository_url='https://webrtc.googlesource.com/src',
        patch_project='webrtc') +
    api.platform.name('linux') +
    base_unittests_additional_compile_target() +
    suppress_analyze(more_exclusions=['third_party/webrtc/f.*']) +
    api.step_data('compile (with patch)', retcode=1)
  )

  yield (
    api.test('use_skia_patch_on_chromium_trybot') +
    props(builder='win7_chromium_rel_ng',
          mastername='tryserver.chromium.win',
          repository='https://skia.googlesource.com/skia',
          patch_repository_url='https://skia.googlesource.com/skia',
          patch_project='skia') +
    api.platform.name('win')
  )

  # Tests that we run nothing if analyze said we didn't have to run anything
  # and there were no source file changes.
  yield (
    api.test('analyze_runs_nothing_with_no_source_file_changes') +
    props(
      mastername='tryserver.chromium.win',
      builder='old_chromium_rel_ng',
      swarm_hashes={}
    ) +
    api.platform.name('win') +
    api.override_step_data('analyze', api.chromium.analyze_builds_nothing) +
    api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output('README.md\nfoo/bar/baz.py')
    )
  )

  swarmed_webkit_tests = (
    props(extra_swarmed_tests=['blink_web_tests']) +
    api.platform.name('linux') +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
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
    ) +
    suppress_analyze()
  )

  # This tests what happens if something goes horribly wrong in
  # run_web_tests.py and we return an internal error; the step should
  # be considered a hard failure and we shouldn't try to compare the
  # lists of failing tests.
  # 255 == test_run_results.UNEXPECTED_ERROR_EXIT_STATUS in run_web_tests.py.
  yield (
    api.test('swarmed_webkit_tests_unexpected_error') +
    swarmed_webkit_tests +
    api.override_step_data('blink_web_tests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, swarming=True,
            isolated_script_passing=False,
            isolated_script_retcode=255) +
        api.swarming.canned_summary_output(failure=True))
  )

  # TODO(dpranke): crbug.com/357866 . This tests what happens if we exceed the
  # number of failures specified with --exit-after-n-crashes-or-times or
  # --exit-after-n-failures; the step should be considered a hard failure and
  # we shouldn't try to compare the lists of failing tests.
  # 130 == test_run_results.INTERRUPTED_EXIT_STATUS in run_web_tests.py.
  yield (
    api.test('swarmed_webkit_tests_interrupted') +
    swarmed_webkit_tests +
    api.override_step_data('blink_web_tests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, swarming=True,
            isolated_script_passing=False,
            isolated_script_retcode=130) +
        api.swarming.canned_summary_output(failure=True))
  )

  # This tests what happens if we don't trip the thresholds listed
  # above, but fail more tests than we can safely fit in a return code.
  # (this should be a soft failure and we can still retry w/o the patch
  # and compare the lists of failing tests).
  yield (
    api.test('swarmed_layout_tests_too_many_failures_for_retcode') +
    swarmed_webkit_tests +
    api.override_step_data('blink_web_tests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, swarming=True,
            isolated_script_passing=False,
            isolated_script_retcode=125) +
        api.swarming.canned_summary_output(failure=True)) +
    api.override_step_data('blink_web_tests (without patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True,
            isolated_script_passing=True) +
        api.swarming.canned_summary_output())
  )

  yield (
    api.test('use_skia_patch_on_blink_trybot') +
    props(mastername='tryserver.blink',
          builder='mac10.12_blink_rel',
          repository='https://skia.googlesource.com/skia',
          patch_repository_url='https://skia.googlesource.com/skia',
          patch_project='skia') +
    api.platform.name('mac')
  )

  yield (
    api.test('use_v8_patch_on_blink_trybot') +
    props(mastername='tryserver.blink',
          builder='mac10.12_blink_rel',
          repository='https://chromium.googlesource.com/v8/v8',
          patch_repository_url='https://chromium.googlesource.com/v8/v8',
          patch_project='v8') +
    api.platform.name('mac')
  )


  def check_ordering(check, step_odict, *steps):
      test_steps = [
          'test_pre_run (with patch).[error] 10_gtest (with patch)',
          'test_pre_run (with patch).[error] 6_isolated_tests (with patch)',
          'test_pre_run (with patch).[error] 5_gtest (with patch)',
          'test_pre_run (with patch).[error] 3_isolated_tests (with patch)',
          'test_pre_run (with patch).[error] 2_isolated_tests (with patch)',
          'test_pre_run (with patch).[error] 1_gtest (with patch)',
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
  yield (
      api.test('sorted') +
      props(extra_swarmed_tests=[
          '1_gtest', '2_isolated_tests', '3_isolated_tests',
          '5_gtest', '6_isolated_tests', '10_gtest']) +
      api.platform.name('linux') +
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
          })
      ) +
      suppress_analyze() +
      api.post_process(check_ordering) +
      api.post_process(DropExpectation)
  )

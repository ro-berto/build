# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'build',
  'depot_tools/bot_update',
  'chromium',
  'chromium_android',
  'chromium_checkout',
  'chromium_swarming',
  'chromium_tests',
  'commit_position',
  'file',
  'filter',
  'depot_tools/gclient',
  'isolate',
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
  'depot_tools/tryserver',
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
            buildername='linux_chromium_rel_ng', extra_swarmed_tests=None,
            **kwargs):
    kwargs.setdefault('path_config', 'kitchen')
    kwargs.setdefault('revision', None)
    swarm_hashes = {}
    if extra_swarmed_tests:
      for test in extra_swarmed_tests:
        swarm_hashes[test] = '[dummy hash for %s]' % test
    return api.properties.tryserver(
      build_config=config,
      mastername=mastername,
      buildername=buildername,
      swarm_hashes=swarm_hashes,
      **kwargs
    )

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

  yield (
    api.test('chromeos_analyze') +
    api.platform.name('linux') +
    props(mastername='tryserver.chromium.linux',
          buildername='chromeos_amd64-generic_chromium_compile_only_ng')
  )

  # Regression test for http://crbug.com/453471#c16
  yield (
    api.test('clobber_analyze') +
    props(buildername='linux_chromium_clobber_rel_ng') +
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
          buildername='win_chromium_rel_ng') +
    api.platform.name('win') +
    suppress_analyze() +
    api.override_step_data('process_dumps', retcode=1)
  )

  yield (
    api.test('invalid_results') +
    props() +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'gtest_tests': ['base_unittests'],
            },
        })
    ) +
    suppress_analyze() +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False)) +
    api.override_step_data('base_unittests (without patch)',
                           api.test_utils.raw_gtest_output(None, retcode=1))
  )

  yield (
    api.test('script_test_with_overridden_compile_targets') +
    props() +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'scripts': [
                    {
                        'name': 'script_test',
                        'script': 'fake_script.py',
                        'override_compile_targets': ['overridden_target']
                    }
                ],
            }
        })
    )
  )

  yield (
    api.test('dynamic_isolated_script_test_on_trybot_passing') +
    props(extra_swarmed_tests=['telemetry_gpu_unittests']) +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
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
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
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
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
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
        })
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
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'telemetry_gpu_unittests',
                      'name': 'telemetry_gpu_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
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
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
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
        })
    ) +
    suppress_analyze()
  )

  yield (
    api.test('swarming_trigger_failure') +
    props() +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'gtest_tests': [
                    {
                      'test': 'base_unittests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
    ) +
    suppress_analyze()
  )

  yield (
    api.test('swarming_test_failure') +
    props(extra_swarmed_tests=['gl_tests']) +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'gtest_tests': [
                    {
                      'test': 'gl_tests',
                      'swarming': {'can_use_on_swarming_builders': True},
                    },
                ],
            },
        })
    ) +
    suppress_analyze() +
    api.override_step_data(
        'gl_tests (with patch)',
        api.swarming.canned_summary_output(failure=True) +
        canned_test(passing=False))
  )

  yield (
    api.test('compile_failure_without_patch_deapply_fn') +
    props() +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
              'gtest_tests': ['base_unittests'],
            },
        })
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
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
              'gtest_tests': ['base_unittests'],
            },
        })
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
    props(buildername='win_chromium_rel_ng',
          mastername='tryserver.chromium.win') +
    api.platform.name('win') +
    api.step_data('gclient runhooks (with patch)', retcode=1) +
    api.step_data('gclient runhooks (without patch)', retcode=1)
  )

  yield (
    api.test('runhooks_failure_ng') +
    api.platform('linux', 64) +
    props(mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
    api.step_data('gclient runhooks (with patch)', retcode=1)
  )

  yield (
    api.test('compile_failure_ng') +
    api.platform('linux', 64) +
    props(mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
    suppress_analyze() +
    api.step_data('compile (with patch)', retcode=1)
  )

  # Test that the component rev for v8 is correctly applied
  # both on the initial checkout and after deapplying the patch.
  yield (
    api.test('compile_failure_with_component_rev') +
    api.platform('linux', 64) +
    props(mastername='tryserver.v8',
          buildername='v8_linux_chromium_gn_rel') +
    api.properties(revision='22135') +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'V8 Linux GN': {
                'additional_compile_targets': ['base_unittests'],
            },
        })
    ) +
    suppress_analyze() +
    api.step_data('compile (with patch)', retcode=1)
  )

  yield (
    api.test('compile_failure_without_patch_ng') +
    api.platform('linux', 64) +
    props(mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
    suppress_analyze() +
    api.step_data('compile (with patch)', retcode=1) +
    api.step_data('compile (without patch)', retcode=1)
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
    props(buildername='linux_chromium_rel_ng', requester='joe@chromium.org',
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
    api.test('recipe_config_changes_not_retried_without_patch') +
    api.properties.tryserver(
      mastername='tryserver.chromium.linux',
      buildername='linux_chromium_chromeos_rel_ng',
      swarm_hashes={}
    ) +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.chromiumos.json)',
        api.json.output({
            'Linux ChromiumOS Tests (1)': {
                'gtest_tests': ['base_unittests'],
            },
        })
    ) +
    suppress_analyze() +
    api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output(
            'testing/buildbot/chromium.chromiumos.json\nfoo/bar/baz.py')
    ) +
    api.override_step_data('base_unittests (with patch)',
                           canned_test(passing=False))
  )

  yield (
    api.test('no_compile_because_of_analyze') +
    props(buildername='linux_chromium_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)', api.json.output({}))
  )

  # This should result in a compile.
  yield (
    api.test('compile_because_of_analyze_matching_exclusion') +
    props(buildername='linux_chromium_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)', api.json.output({})) +
    suppress_analyze()
  )

  # This should result in a compile.
  yield (
    api.test('compile_because_of_analyze') +
    props(buildername='linux_chromium_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)', api.json.output({})) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'compile_targets': [],
                       'test_targets': []}))
  )

  yield (
    api.test('compile_because_of_analyze_with_filtered_tests_no_builder') +
    props(buildername='linux_chromium_rel_ng') +
    api.platform.name('linux') +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'compile_targets': ['browser_tests', 'base_unittests'],
                       'test_targets': ['browser_tests', 'base_unittests']}))
  )

  yield (
    api.test('compile_because_of_analyze_with_filtered_tests') +
    props(buildername='linux_chromium_rel_ng') +
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
    props(buildername='linux_chromium_rel_ng') +
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
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'gtest_tests': ['base_unittests'],
            },
        })
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
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'gtest_tests': ['base_unittests'],
            },
        })
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'invalid_targets': ['invalid target', 'another one']}))
  )

  yield (
    api.test('use_v8_patch_on_chromium_trybot') +
    props(buildername='win_chromium_rel_ng',
          mastername='tryserver.chromium.win',
          patch_project='v8') +
    api.platform.name('win')
  )

  yield (
    api.test('use_webrtc_patch_on_chromium_trybot') +
    props(patch_project='webrtc') +
    api.platform.name('linux')
  )

  yield (
    api.test('use_webrtc_patch_on_chromium_trybot_compile_failure') +
    props(patch_project='webrtc') +
    api.platform.name('linux') +
    suppress_analyze(more_exclusions=['third_party/webrtc/f.*']) +
    api.step_data('compile (with patch)', retcode=1)
  )

  yield (
    api.test('use_skia_patch_on_chromium_trybot') +
    props(buildername='win_chromium_rel_ng',
          mastername='tryserver.chromium.win',
          patch_project='skia') +
    api.platform.name('win')
  )

  # Tests that we run nothing if analyze said we didn't have to run anything
  # and there were no source file changes.
  yield (
    api.test('analyze_runs_nothing_with_no_source_file_changes') +
    api.properties.tryserver(
      mastername='tryserver.chromium.win',
      buildername='win_chromium_rel_ng',
      swarm_hashes={}
    ) +
    api.platform.name('win') +
    api.override_step_data('analyze', api.chromium.analyze_builds_nothing) +
    api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output('README.md\nfoo/bar/baz.py')
    )
  )

  # Test we *do* run the BlinkTest if we touch third_party/WebKit
  yield (
    api.test('add_layout_tests_via_manual_diff_inspection') +
    api.properties.tryserver(
      mastername='tryserver.chromium.win',
      buildername='win_chromium_rel_ng',
      swarm_hashes={}
    ) +
    api.platform.name('win') +
    api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output(
            'third_party/WebKit/Source/core/dom/Element.cpp\n')
    )
  )

  # Test we *don't* run the BlinkTest if we don't touch the right paths
  yield (
    api.test('skip_layout_tests_via_manual_diff_doesnt_match') +
    api.properties.tryserver(
      mastername='tryserver.chromium.win',
      buildername='win_chromium_rel_ng',
      swarm_hashes={}
    ) +
    api.platform.name('win') +
    api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output(
            'base/time.h\n')
    )
  )

  # Test we run the swarming layout tests if we touch third_party/WebKit
  yield (
    api.test('add_swarming_layout_tests_via_manual_diff_inspection') +
    api.properties.tryserver(
      mastername='tryserver.chromium.linux',
      buildername='linux_chromium_rel_ng',
      swarm_hashes={}
    ) +
    props(extra_swarmed_tests=['webkit_layout_tests_exparchive']) +
    api.platform.name('linux') +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'test_targets': ['webkit_layout_tests_exparchive'],
                       'compile_targets': ['webkit_layout_tests_exparchive']})
    ) +
    api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output(
            'third_party/WebKit/Source/core/dom/Element.cpp\n')
    ) +
    api.override_step_data(
        'webkit_layout_tests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True
        ) +
        api.swarming.canned_summary_output()
    )
  )

  yield (
    api.test(
        'add_swarming_layout_tests_via_manual_diff_inspection_that_fails') +
    api.properties.tryserver(
      mastername='tryserver.chromium.linux',
      buildername='linux_chromium_rel_ng',
      swarm_hashes={}
    ) +
    props(extra_swarmed_tests=['webkit_layout_tests_exparchive']) +
    api.platform.name('linux') +
    api.override_step_data(
      'analyze',
      api.json.output({
          'status': 'Found dependency',
          'test_targets': ['webkit_layout_tests_exparchive'],
          'compile_targets': ['webkit_layout_tests_exparchive']})) +
    api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output(
            'third_party/WebKit/Source/core/dom/Element.cpp\n')
    ) +
    api.override_step_data(
        'webkit_layout_tests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True,
            isolated_script_passing=False
        ) +
        api.swarming.canned_summary_output(failure=True)
    ) +
    api.override_step_data(
        'webkit_layout_tests (without patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, is_win=False, swarming=True
        ) +
        api.swarming.canned_summary_output()
    )
  )

  # Test we don't run the swarming layout tests if we don't touch the right
  # paths
  yield (
    api.test('skip_swarming_layout_tests_via_manual_diff_doesnt_match') +
    api.properties.tryserver(
      mastername='tryserver.chromium.linux',
      buildername='linux_chromium_rel_ng',
      swarm_hashes={}
    ) +
    api.platform.name('linux') +
    api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output(
            'base/time.h\n')
    )
  )

  swarmed_webkit_tests = (
    props(extra_swarmed_tests=['webkit_layout_tests']) +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output({
            'Linux Tests': {
                'isolated_scripts': [
                    {
                      'isolate_name': 'webkit_layout_tests',
                      'name': 'webkit_layout_tests',
                      'swarming': {'can_use_on_swarming_builders': True},
                      'results_handler': 'layout tests',
                    },
                ],
            },
        })
    ) +
    suppress_analyze()
  )

  # This tests that if the first fails, but the second pass succeeds
  # that we fail the whole build.
  yield (
    api.test('swarmed_webkit_tests_minimal_pass_continues') +
    swarmed_webkit_tests +
    api.override_step_data('webkit_layout_tests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, swarming=True,
            isolated_script_passing=False)
        + api.swarming.canned_summary_output()) +
    api.override_step_data('webkit_layout_tests (without patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, swarming=True,
            isolated_script_passing=True)
        + api.swarming.canned_summary_output())
  )

  yield (
    api.test('swarmed_webkit_tests_compile_without_patch_fails') +
    swarmed_webkit_tests +
    api.override_step_data('webkit_layout_tests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, swarming=True,
            isolated_script_passing=False) +
        api.swarming.canned_summary_output(failure=True)) +
    api.override_step_data('compile (without patch)', retcode=1)
  )

  # This tests what happens if something goes horribly wrong in
  # run-webkit-tests and we return an internal error; the step should
  # be considered a hard failure and we shouldn't try to compare the
  # lists of failing tests.
  # 255 == test_run_results.UNEXPECTED_ERROR_EXIT_STATUS in run-webkit-tests.
  yield (
    api.test('swarmed_webkit_tests_unexpected_error') +
    swarmed_webkit_tests +
    api.override_step_data('webkit_layout_tests (with patch)',
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
  # 130 == test_run_results.INTERRUPTED_EXIT_STATUS in run-webkit-tests.
  yield (
    api.test('swarmed_webkit_tests_interrupted') +
    swarmed_webkit_tests +
    api.override_step_data('webkit_layout_tests (with patch)',
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
    api.override_step_data('webkit_layout_tests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, swarming=True,
            isolated_script_passing=False,
            isolated_script_retcode=125) +
        api.swarming.canned_summary_output(failure=True)) +
    api.override_step_data('webkit_layout_tests (without patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True,
            isolated_script_passing=True) +
        api.swarming.canned_summary_output())
  )

  yield (
    api.test('swarmed_layout_tests_with_and_without_patch_fail') +
    swarmed_webkit_tests +
    api.override_step_data('webkit_layout_tests (with patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, swarming=True,
            isolated_script_passing=False) +
        api.swarming.canned_summary_output(failure=True)) +
    api.override_step_data('webkit_layout_tests (without patch)',
        api.test_utils.canned_isolated_script_output(
            passing=True, swarming=True,
            isolated_script_passing=True) +
        api.swarming.canned_summary_output(failure=True))
  )

  yield (
    api.test('non_cq_blink_tryjob') +
    props(mastername='tryserver.blink',
          buildername='win7_blink_rel',
          requester='someone@chromium.org') +
    suppress_analyze() +
    api.platform.name('win') +
    api.override_step_data('webkit_tests (with patch)',
                           api.test_utils.canned_test_output(passing=True))
  )

  yield (
    api.test('use_skia_patch_on_blink_trybot') +
    props(mastername='tryserver.blink',
          buildername='mac10.9_blink_rel',
          patch_project='skia') +
    api.platform.name('mac')
  )

  yield (
    api.test('use_v8_patch_on_blink_trybot') +
    props(mastername='tryserver.blink',
          buildername='mac10.9_blink_rel',
          patch_project='v8') +
    api.platform.name('mac')
  )

  yield (
    api.test('dont_deapply_patch') +
    props(mastername='tryserver.chromium.mac',
          buildername='mac_optional_gpu_tests_rel') +
    api.platform.name('mac') +
    api.override_step_data(
        'read test spec (chromium.gpu.fyi.json)',
        api.json.output({
            'Optional Mac Retina Release (NVIDIA)': {
                'gtest_tests': ['base_unittests'],
            },
        })
    ) +
    suppress_analyze()
  )

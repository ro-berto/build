# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium
from RECIPE_MODULES.build.chromium_tests import (steps, try_spec as
                                                 try_spec_module)

DEPS = [
    'chromium',
    'chromium_tests',
    'code_coverage',
    'pgo',
    'profiles',
    'recipe_engine/buildbucket',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  builder_id = api.chromium.get_builder_id()
  try_spec = api.chromium_tests.trybots.get(builder_id)
  if try_spec is None:
    try_spec = try_spec_module.TrySpec.create(mirrors=[builder_id])

  bot_config = api.chromium_tests.create_bot_config_object(try_spec.mirrors)
  api.chromium_tests.configure_build(bot_config)
  # Fake path.
  api.profiles._merge_scripts_dir = api.path['start_dir']
  # We're forcing the root profile dir to '/', such that the file.listdir
  # call being made by ensure_profdata_files can be overridden in the test run.
  # There's no way to translate a generated Path object into a string in
  # the current GenTest structure.
  api.profiles._root_profile_dir = api.path.get('/')

  if api.properties.get('mock_merged_profdata', True):
    api.path.mock_add_paths(
        api.profiles.profile_dir().join('pgo_final_aggregate.profdata'))

  tests = [
      steps.SwarmingIsolatedScriptTest('performance_test_suite'),
      steps.SwarmingIsolatedScriptTest('different_test_suite'),
  ]

  for test in tests:
    step = test.name
    # Preprocessing for test
    test._test_runs = {
        '': {
            'valid': api.properties.get('benchmark_result', True),
            'failures': api.properties.get('benchmark_failures', []),
        }
    }
    # shard_merge already ensures the profile_subdir is generated w/ step_name
    api.code_coverage.shard_merge(
        step, test.target_name, additional_merge=getattr(test, '_merge', None))

  api.pgo.process_pgo_data(tests)

  # coverage only
  _ = api.pgo.using_pgo


def GenTests(api):

  yield api.test(
      'merged profdata does not exist',
      api.chromium.generic_build(
          builder_group='chromium.perf', builder='mac-builder-perf'),
      api.pgo(use_pgo=True),
      api.platform('mac', 64),
      api.properties(mock_merged_profdata=False),
      api.override_step_data(
          'validate benchmark results and profile data.searching for '
          'profdata files',
          api.file.listdir([
              '/performance_test_suite/performance_test_suite.profdata',
              '/different_test_suite/different_test_suite.profdata'
          ])),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.No profdata was generated.'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic windows',
      api.chromium.generic_build(
          builder_group='chromium.perf', builder='win64-builder-perf'),
      api.pgo(use_pgo=True),
      api.platform('win', 64),
      api.properties(mock_merged_profdata=True),
      api.override_step_data(
          'validate benchmark results and profile data.searching for '
          'profdata files',
          api.file.listdir([
              '\\\\performance_test_suite\\\\performance_test_suite.profdata',
              '\\\\different_test_suite\\\\different_test_suite.profdata'
          ])),
      api.post_process(post_process.MustRunRE, 'ensure profile dir for .*'),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.gsutil upload artifact to GS'),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.Rename the profdata artifact'),
      api.post_process(post_process.MustRun,
                       'Processing PGO .profraw data.git show'),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.merge all profile files into a single'
          ' .profdata'),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.Finding profile merge errors'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(
          post_process.StepCommandContains,
          'Processing PGO .profraw data.gsutil upload artifact to GS', [
              'gs://chromium-optimization-profiles/pgo_profiles/'
              'chrome-win64-master-1587876258-'
              'ade24b3118b1feaa04cb4406253403f3f72a7f0e.profdata'
          ]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'merge errors',
      api.chromium.generic_build(
          builder_group='chromium.perf', builder='mac-builder-perf'),
      api.pgo(use_pgo=True),
      api.platform('mac', 64),
      api.properties(mock_merged_profdata=True),
      api.override_step_data(
          'validate benchmark results and profile data.searching for '
          'profdata files',
          api.file.listdir([
              '/performance_test_suite/performance_test_suite.profdata',
              '/different_test_suite/different_test_suite.profdata'
          ])),
      api.override_step_data(
          'Processing PGO .profraw data.Finding profile merge errors',
          stdout=api.json.output({
              "failed profiles": {
                  "browser_tests": ["/tmp/1/default-123.profraw"]
              },
              "total": 1
          })),
      api.post_process(
          post_process.MustRun,
          'Processing PGO .profraw data.Failing due to merge errors found '
          'alongside invalid profile data.'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'missing profdata file',
      api.chromium.generic_build(
          builder_group='chromium.perf', builder='win64-builder-perf'),
      api.pgo(use_pgo=True),
      api.platform('win', 64),
      api.properties(mock_merged_profdata=False),
      api.post_process(
          post_process.MustRun, 'validate benchmark results and profile data.'
          'searching for profdata files'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'one test missing profdata file',
      api.chromium.generic_build(
          builder_group='chromium.perf', builder='win64-builder-perf'),
      api.pgo(use_pgo=True),
      api.platform('win', 64),
      api.properties(mock_merged_profdata=False),
      api.override_step_data(
          'validate benchmark results and profile data.searching for '
          'profdata files',
          api.file.listdir(
              ['/performance_test_suite/performance_test_suite.profdata'])),
      api.post_process(
          post_process.MustRun, 'validate benchmark results and profile data.'
          'searching for profdata files'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'invalid benchmark test',
      api.chromium.generic_build(
          builder_group='chromium.perf', builder='win64-builder-perf'),
      api.pgo(use_pgo=True),
      api.platform('win', 64),
      api.properties(mock_merged_profdata=False, benchmark_result=False),
      api.override_step_data(
          'validate benchmark results and profile data.searching for '
          'profdata files',
          api.file.listdir(
              ['/performance_test_suite/performance_test_suite.profdata'])),
      api.post_process(
          post_process.MustRun, 'validate benchmark results and profile data.'
          'searching for profdata files'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failed benchmark test',
      api.chromium.generic_build(
          builder_group='chromium.perf', builder='win64-builder-perf'),
      api.pgo(use_pgo=True),
      api.platform('win', 64),
      api.properties(mock_merged_profdata=False, benchmark_failures=['test1']),
      api.override_step_data(
          'validate benchmark results and profile data.searching for '
          'profdata files',
          api.file.listdir(
              ['/performance_test_suite/performance_test_suite.profdata'])),
      api.post_process(
          post_process.MustRun, 'validate benchmark results and profile data.'
          'searching for profdata files'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'trybot',
      api.chromium.generic_build(
          builder_group='chromium.perf', builder='win64-builder-perf'),
      api.pgo(use_pgo=True, skip_profile_upload=True),
      api.platform('win', 64),
      api.properties(mock_merged_profdata=True),
      api.override_step_data(
          'validate benchmark results and profile data.searching for '
          'profdata files',
          api.file.listdir([
              '\\\\performance_test_suite\\\\performance_test_suite.profdata',
              '\\\\different_test_suite\\\\different_test_suite.profdata'
          ])),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  ) + api.post_process(post_process.DoesNotRunRE,
                       '.*gsutil upload artifact to GS.*')

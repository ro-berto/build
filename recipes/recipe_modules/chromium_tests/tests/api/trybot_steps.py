# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build.chromium_tests_builder_config import try_spec
from RECIPE_MODULES.depot_tools.tryserver import api as tryserver

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'depot_tools/tryserver',
    'filter',
    'pgo',
    'profiles',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/buildbucket',
    'test_utils',
]

_TEST_BUILDERS = ctbc.BuilderDatabase.create({
    'chromium.test': {
        'chromium-rel':
            ctbc.BuilderSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
            ),
        'retry-shards':
            ctbc.BuilderSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
            ),
        'retry-shards-test':
            ctbc.BuilderSpec.create(
                execution_mode=ctbc.TEST,
                parent_buildername='retry-shards',
            ),
    },
    'tryserver.chromium.unmirrored': {
        'unmirrored-chromium-rel':
            ctbc.BuilderSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
            ),
    },
})

_TEST_TRYBOTS = ctbc.TryDatabase.create({
    'tryserver.chromium.test': {
        'retry-shards':
            ctbc.TrySpec.create(
                retry_failed_shards=True,
                mirrors=[
                    ctbc.TryMirror.create(
                        builder_group='chromium.test',
                        buildername='retry-shards',
                        tester='retry-shards-test',
                    ),
                ],
            ),
        'rts-rel':
            ctbc.TrySpec.create(
                mirrors=[
                    ctbc.TryMirror.create(
                        builder_group='chromium.test',
                        buildername='chromium-rel',
                        tester='chromium-rel',
                    ),
                ],
                regression_test_selection=try_spec.QUICK_RUN_ONLY,
            ),
    }
})


def RunSteps(api):
  assert api.tryserver.is_tryserver
  api.path.mock_add_paths(
      api.profiles.profile_dir().join('overall-merged.profdata'))
  api.path.mock_add_paths(api.profiles.profile_dir().join(
      api.pgo.TEMP_PROFDATA_FILENAME))

  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  raw_result = api.chromium_tests.trybot_steps(builder_id, builder_config)
  return raw_result


def GenTests(api):
  yield api.test(
      'basic',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.filter.suppress_analyze(),
  )

  yield api.test(
      'basic-branch',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.properties(root_solution_revision='refs/branch-heads/4472'),
      api.filter.suppress_analyze(),
  )

  yield api.test(
      'analyze_compile_mode',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux',
          builder='linux_chromium_clobber_rel_ng'),
  )

  yield api.test(
      'analyze_names',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='fuchsia_x64'),
      api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
              'base': {
                  'exclusions': []
              },
              'chromium': {
                  'exclusions': []
              },
              'fuchsia': {
                  'exclusions': ['path/to/fuchsia/exclusion.py']
              },
          })),
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('path/to/fuchsia/exclusion.py')),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_compile',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
  )

  yield api.test(
      'no_compile_no_source',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.override_step_data('git diff to analyze patch',
                             api.raw_io.stream_output('OWNERS')),
  )

  yield api.test(
      'unmirrored',
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.unmirrored',
          builder='unmirrored-chromium-rel',
          builder_db=_TEST_BUILDERS,
          try_db=None),
      api.chromium_tests.read_source_side_spec(
          'tryserver.chromium.unmirrored', {
              'unmirrored-chromium-rel': {
                  'gtest_tests': ['bogus_unittests'],
              },
          }),
      api.filter.suppress_analyze(),
      api.post_process(post_process.MustRun, 'bogus_unittests (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'dummy-tester',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-group', builder='fake-try-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'fake-group': {
                  'fake-builder':
                  ctbc.BuilderSpec.create(
                      chromium_config='chromium',
                      gclient_config='chromium',
                  ),
                  'fake-dummy-tester':
                  ctbc.BuilderSpec.create(
                      execution_mode=ctbc.PROVIDE_TEST_SPEC),
              },
          }),
          try_db=ctbc.TryDatabase.create({
              'fake-group': {
                  'fake-try-builder':
                  ctbc.TrySpec.create(mirrors=[
                      ctbc.TryMirror.create(
                          builder_group='fake-group',
                          buildername='fake-builder',
                          tester='fake-dummy-tester',
                      )
                  ]),
              },
          })),
      api.filter.suppress_analyze(),
      api.chromium_tests.read_source_side_spec(
          'fake-group',
          {
              'fake-dummy-tester': {
                  'gtest_tests': [{
                      'test': 'fake-test',
                  }],
              },
          },
      ),
      api.post_check(
          lambda check, steps: \
          check('fake-test' in steps['compile (with patch)'].cmd)
      ),
      api.post_check(post_process.MustRun, 'fake-test (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  CUSTOM_PROPS = sum([
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.test',
          builder='retry-shards',
          builder_db=_TEST_BUILDERS,
          try_db=_TEST_TRYBOTS),
      api.properties(
          swarm_hashes={'base_unittests': '[dummy hash for base_unittests]'},),
  ], api.empty_test_data())

  yield api.test(
      'retry_shards',
      CUSTOM_PROPS,
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'retry-shards': {
                  'gtest_tests': [{
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.filter.suppress_analyze(),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_without_patch',
      CUSTOM_PROPS,
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'retry-shards': {
                  'gtest_tests': [{
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.filter.suppress_analyze(),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'base_unittests (without patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_invalid',
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.test',
          builder='retry-shards',
          builder_db=_TEST_BUILDERS,
          try_db=_TEST_TRYBOTS),
      api.properties(
          swarm_hashes={'base_unittests': '[dummy hash for base_unittests]'}),
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'retry-shards': {
                  'gtest_tests': [{
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results('invalid_results', 1),
              failure=True)),
      api.filter.suppress_analyze(),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_invalid_retry',
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.test',
          builder='retry-shards',
          builder_db=_TEST_BUILDERS,
          try_db=_TEST_TRYBOTS),
      api.properties(
          swarm_hashes={'base_unittests': '[dummy hash for base_unittests]'}),
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'retry-shards': {
                  'gtest_tests': [{
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results('invalid results', 1),
              failure=True)),
      api.filter.suppress_analyze(),
      api.post_process(post_process.MustRun, 'base_unittests (with patch)'),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'base_unittests (without patch)'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_all_invalid_results',
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.test',
          builder='retry-shards',
          builder_db=_TEST_BUILDERS,
          try_db=_TEST_TRYBOTS),
      api.properties(
          swarm_hashes={'base_unittests': '[dummy hash for base_unittests]'}),
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'retry-shards': {
                  'gtest_tests': [{
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results('invalid results', 1),
              failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.gtest_results('invalid results', 1),
              failure=True)),
      api.filter.suppress_analyze(),
      api.post_process(post_process.MustRun, 'base_unittests (with patch)'),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage_trybot_with_patch',
      api.code_coverage(use_clang_coverage=True),
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          swarm_hashes={'base_unittests': '[dummy hash for base_unittests]'}),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'isolate_coverage_data': True,
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.filter.suppress_analyze(),
      api.post_process(post_process.MustRun, 'base_unittests (with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)'),
      api.post_process(
          # Only generates coverage data for the with patch step.
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in 1 tests'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage_trybot_retry_shards_with_patch',
      api.code_coverage(use_clang_coverage=True),
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          swarm_hashes={'base_unittests': '[dummy hash for base_unittests]'}),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'isolate_coverage_data': True,
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.filter.suppress_analyze(),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.post_process(post_process.MustRun, 'base_unittests (with patch)'),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)'),
      api.post_process(
          # Generates coverage data for the with patch and retry shards with
          # patch steps.
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in 2 tests'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage_trybot_without_patch',
      api.code_coverage(use_clang_coverage=True),
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          swarm_hashes={'base_unittests': '[dummy hash for base_unittests]'}),
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [{
                      'isolate_coverage_data': True,
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.filter.suppress_analyze(),
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.post_process(post_process.MustRun, 'base_unittests (with patch)'),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'base_unittests (without patch)'),
      api.post_process(
          # Generates coverage data for the with patch and retry shards with
          # patch steps. Without patch steps are always ignored.
          post_process.MustRun,
          'process clang code coverage data for overall test coverage.generate '
          'metadata for overall test coverage in 2 tests'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'pgo_trybot',
      api.chromium.try_build(
          builder_group='tryserver.chromium.perf', builder='Mac Builder Perf'),
      api.properties(
          swarm_hashes={
              'performance_test_suite':
                  '[dummy hash for performance_test_suite]'
          },),
      api.pgo(use_pgo=True, skip_profile_upload=True),
      api.platform('mac', 64),
      api.chromium_tests.read_source_side_spec(
          'chromium.perf', {
              'mac-builder-perf': {
                  'isolated_scripts': [{
                      'name': 'performance_test_suite',
                      'isolate_profile_data': True,
                      'test': 'performance_test_suite',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.filter.suppress_analyze(),
      api.override_step_data(
          'validate benchmark results and profile data.searching for '
          'profdata files',
          api.file.listdir([('/performance_test_suite_with_patch/'
                             'performance_test_suite.profdata')])),
      api.post_process(post_process.DoesNotRunRE,
                       '.*gsutil upload artifact to GS.*'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  canned_test = api.test_utils.canned_gtest_output

  def multiple_base_unittests_additional_compile_target():
    return api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'gtest_tests': [
                    'base_unittests1', 'base_unittests2', 'base_unittests3'
                ],
            },
        })

  yield api.test(
      'many_invalid_results',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      multiple_base_unittests_additional_compile_target(),
      api.filter.suppress_analyze(),
      api.chromium_tests.change_size_limit(2),
      api.override_step_data('base_unittests1 (with patch)',
                             canned_test(passing=False,
                                         legacy_annotation=True)),
      api.override_step_data('base_unittests1 (without patch)',
                             api.legacy_annotation.failure_step),
      api.override_step_data('base_unittests2 (with patch)',
                             canned_test(passing=False,
                                         legacy_annotation=True)),
      api.override_step_data('base_unittests2 (without patch)',
                             api.legacy_annotation.failure_step),
      api.override_step_data('base_unittests3 (with patch)',
                             canned_test(passing=False,
                                         legacy_annotation=True)),
      api.override_step_data('base_unittests3 (without patch)',
                             api.legacy_annotation.failure_step),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.ResultReasonRE,
                       r'3 Test Suite\(s\) failed.*'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic dryrun',
      api.properties(dry_run=True),
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.filter.suppress_analyze(),
  )

  yield api.test(
      'quick run rts',
      api.properties(
          **{
              "$recipe_engine/cq": {
                  "active": True,
                  "dryRun": True,
                  "runMode": "QUICK_DRY_RUN",
                  "topLevel": True
              }
          }),
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.test',
          builder='rts-rel',
          builder_db=_TEST_BUILDERS,
          try_db=_TEST_TRYBOTS,
      ),
      api.chromium_tests.read_source_side_spec('chromium.test', {
          'chromium-rel': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(post_process.DropExpectation),
      api.filter.suppress_analyze(),
  )

  yield api.test(
      'depend_on_footer_failure',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.step_data(
          'parse description',
          api.json.output(
              {tryserver.constants.CQ_DEPEND_FOOTER: 'chromium:123456'})),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.ResultReasonRE,
                       r'Commit message footer Cq-Depend is not supported.*'),
      api.post_process(post_process.DropExpectation),
  )

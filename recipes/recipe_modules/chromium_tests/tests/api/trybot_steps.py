# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build.chromium_tests_builder_config import try_spec
from RECIPE_MODULES.depot_tools.tryserver import api as tryserver

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import common as resultdb_common
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2
from PB.go.chromium.org.luci.analysis.proto.v1 import test_history

DEPS = [
    'chromium',
    'chromium_android',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'code_coverage',
    'depot_tools/tryserver',
    'filter',
    'flakiness',
    'pgo',
    'profiles',
    'recipe_engine/buildbucket',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
    'recipe_engine/luci_analysis',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'recipe_engine/swarming',
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
        'disable-retry-wo-patch':
            ctbc.TrySpec.create(
                retry_failed_shards=True,
                retry_without_patch=False,
                mirrors=[
                    ctbc.TryMirror.create(
                        builder_group='chromium.test',
                        buildername='retry-shards',
                        tester='retry-shards-test',
                    ),
                ],
            ),
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
        'rts-exp-rel':
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
        'inverted-rts-rel':
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
  ctbc_api = api.chromium_tests_builder_config

  yield api.test(
      'basic',
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {
              'gtest_tests': ['base_unittests'],
          },
      }),
  )

  yield api.test(
      'basic-branch',
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.properties(root_solution_revision='refs/branch-heads/4472'),
  )

  yield api.test(
      'analyze_compile_mode',
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group', builder='fake-try-builder'),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
              builder_spec=ctbc.BuilderSpec.create(
                  gclient_config='chromium',
                  chromium_config='chromium',
                  chromium_apply_config=['clobber'],
              ),
          ).assemble()),
  )

  yield api.test(
      'no_compile',
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
  )

  yield api.test(
      'no_compile_no_source',
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.override_step_data('git diff to analyze patch',
                             api.raw_io.stream_output('OWNERS')),
  )

  yield api.test(
      'unmirrored',
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.unmirrored',
          builder='unmirrored-chromium-rel',
          builder_db=_TEST_BUILDERS,
          try_db=None,
      ),
      api.chromium_tests.read_source_side_spec(
          'tryserver.chromium.unmirrored', {
              'unmirrored-chromium-rel': {
                  'gtest_tests': ['bogus_unittests'],
              },
          }),
      api.post_process(post_process.MustRun, 'bogus_unittests (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  def custom_props():
    return sum([
        api.chromium_tests_builder_config.try_build(
            builder_group='tryserver.chromium.test',
            builder='retry-shards',
            builder_db=_TEST_BUILDERS,
            try_db=_TEST_TRYBOTS,
        ),
        api.properties(
            swarm_hashes={
                'base_unittests': '[dummy hash for base_unittests/size]'
            },),
    ], api.empty_test_data())

  yield api.test(
      'retry_shards',
      custom_props(),
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
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_without_patch',
      custom_props(),
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
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'retry shards with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'without patch', failures=['Test.One']),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'base_unittests (without patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'without_patch_notrun_failure',
      custom_props(),
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
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'retry shards with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'without patch', skips=['Test.One']),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.MustRun, 'base_unittests (without patch)'),
      # A test that exits with FAILURE in 'with patch' then NOTRUN in
      # 'without patch' should fail the build.
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'retry_shards_invalid',
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.test',
          builder='retry-shards',
          builder_db=_TEST_BUILDERS,
          try_db=_TEST_TRYBOTS,
      ),
      api.properties(swarm_hashes={
          'base_unittests': '[dummy hash for base_unittests/size]'
      }),
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
          try_db=_TEST_TRYBOTS,
      ),
      api.properties(swarm_hashes={
          'base_unittests': '[dummy hash for base_unittests/size]'
      }),
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
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'retry shards with patch', failures=['Test.One']),
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
          try_db=_TEST_TRYBOTS,
      ),
      api.properties(swarm_hashes={
          'base_unittests': '[dummy hash for base_unittests/size]'
      }),
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
      api.post_process(post_process.MustRun, 'base_unittests (with patch)'),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'disable_retry_without_patch',
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.test',
          builder='disable-retry-wo-patch',
          builder_db=_TEST_BUILDERS,
          try_db=_TEST_TRYBOTS,
      ),
      api.properties(swarm_hashes={
          'base_unittests': '[dummy hash for base_unittests/size]'
      }),
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
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'retry shards with patch', failures=['Test.One']),
      api.post_process(post_process.MustRun,
                       'base_unittests (retry shards with patch)'),
      api.post_process(post_process.DoesNotRun,
                       'base_unittests (without patch)'),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'code_coverage_trybot_with_patch',
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.code_coverage(use_clang_coverage=True),
      api.properties(swarm_hashes={
          'base_unittests': '[dummy hash for base_unittests/size]'
      }),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'gtest_tests': [{
                      'isolate_coverage_data': True,
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
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
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.code_coverage(use_clang_coverage=True),
      api.properties(swarm_hashes={
          'base_unittests': '[dummy hash for base_unittests/size]'
      }),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'gtest_tests': [{
                      'isolate_coverage_data': True,
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
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.code_coverage(use_clang_coverage=True),
      api.properties(swarm_hashes={
          'base_unittests': '[dummy hash for base_unittests/size]'
      }),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'gtest_tests': [{
                      'isolate_coverage_data': True,
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'with patch', failures=['Test.One']),
      api.chromium_tests.gen_swarming_and_rdb_results(
          'base_unittests', 'retry shards with patch', failures=['Test.One']),
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
      api.chromium_tests_builder_config.try_build(
          builder_group='pgo-try-group',
          builder='pgo-try-builder',
          builder_db=ctbc.BuilderDatabase.create({
              'pgo-group': {
                  'pgo-builder':
                      ctbc.BuilderSpec.create(
                          android_config='main_builder',
                          chromium_config='android',
                          chromium_config_kwargs={
                              'BUILD_CONFIG': 'Release',
                              'TARGET_BITS': 32,
                              'TARGET_PLATFORM': 'android',
                          },
                          gclient_config='chromium',
                          gclient_apply_config=['android'],
                          simulation_platform='linux',
                      ),
              },
          }),
          try_db=ctbc.TryDatabase.create({
              'pgo-try-group': {
                  'pgo-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          'pgo-group', 'pgo-builder'),
              },
          }),
      ),
      api.properties(
          swarm_hashes={
              'performance_test_suite':
                  '[dummy hash for performance_test_suite/size]'
          },),
      api.pgo(use_pgo=True, skip_profile_upload=True),
      api.platform('linux', 64),
      api.chromium_tests.read_source_side_spec(
          'pgo-group', {
              'pgo-builder': {
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

  yield api.test(
      'many_invalid_results',
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'gtest_tests':
                      ['base_unittests1', 'base_unittests2', 'base_unittests3'],
              },
          }),
      api.chromium_tests.change_size_limit(2),
      api.override_step_data(
          'base_unittests1 results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'base_unittests1', failing_tests=['Test.One']))),
      api.override_step_data(
          'base_unittests2 results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'base_unittests2', failing_tests=['Test.One']))),
      api.override_step_data(
          'base_unittests3 results',
          stdout=api.raw_io.output_text(
              api.test_utils.rdb_results(
                  'base_unittests3', failing_tests=['Test.One']))),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.ResultReasonRE,
                       r'3 Test Suite\(s\) failed.*'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic dryrun',
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.properties(dry_run=True),
      api.chromium_tests.read_source_side_spec('fake-group', {
          'fake-builder': {
              'gtest_tests': ['base_unittests'],
          },
      }),
  )

  yield api.test(
      'quick run experimental rts',
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
          builder='rts-exp-rel',
          builder_db=_TEST_BUILDERS,
          try_db=_TEST_TRYBOTS,
          experiments=['chromium_rts.experimental_model'],
      ),
      api.chromium_tests.read_source_side_spec('chromium.test', {
          'chromium-rel': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(post_process.PropertyEquals, 'rts_setting',
                       'rts-ml-chromium'),
      api.post_process(post_process.DropExpectation),
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
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'chromium-rel': {
                  'gtest_tests': [{
                      'test':
                          'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      },
                      'args': [
                          '--test-launcher-filter-file=../../testing/buildbot/filters/ozone-linux.interactive_ui_tests_wayland.filter',
                      ],
                  }],
              },
          }),
      api.step_data(
          'find rts command lines (with patch)',
          api.json.output({
              'base_unittests': [
                  './%s' % 'base_unittests', '--fake-without-patch-flag',
                  '--fake-log-file', '$ISOLATED_OUTDIR/fake.log',
                  '--test-launcher-filter-file=base_unittests.filter'
              ]
          })),
      api.post_check(
          api.swarming.check_triggered_request,
          'test_pre_run (with patch).[trigger] base_unittests (with patch)',
          lambda check, req: check(
              '--test-launcher-filter-file=../../testing/buildbot/filters/ozone-linux.interactive_ui_tests_wayland.filter;base_unittests.filter'
              in req[0].command)),
      api.post_check(
          api.swarming.check_triggered_request,
          'test_pre_run (with patch).[trigger] base_unittests (with patch)',
          lambda check, req: check(
              '--test-launcher-filter-file=../../testing/buildbot/filters/ozone-linux.interactive_ui_tests_wayland.filter'
              not in req[0].command)),
      api.post_check(
          api.swarming.check_triggered_request,
          'test_pre_run (with patch).[trigger] base_unittests (with patch)',
          lambda check, req: check(
              '--test-launcher-filter-file=base_unittests.filter' \
                not in req[0].command)),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(post_process.MustRun, 'RTS was used'),
      api.post_process(post_process.PropertyEquals, 'rts_setting',
                       'rts-chromium'),
      api.post_process(post_process.PropertyEquals, 'rts_was_used', True),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'rts enabled on dry run experiment',
      api.properties(
          **{
              "$recipe_engine/cq": {
                  "active": True,
                  "dryRun": True,
                  "runMode": "DRY_RUN",
                  "topLevel": True
              }
          }),
      api.chromium_tests_builder_config.try_build(
          builder_group='tryserver.chromium.test',
          builder='rts-rel',
          builder_db=_TEST_BUILDERS,
          try_db=_TEST_TRYBOTS,
          # This change number will result in a value of 0 compared to the
          # threshold ensuring it runs if any run is capable
          change_number=25,
      ),
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'chromium-rel': {
                  'gtest_tests': [{
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.step_data(
          'find rts command lines (with patch)',
          api.json.output({
              'base_unittests': [
                  './%s' % 'base_unittests', '--fake-without-patch-flag',
                  '--fake-log-file', '$ISOLATED_OUTDIR/fake.log',
                  '-filter=base_unittests.filter'
              ]
          })),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(post_process.StepTextContains, 'quick run options',
                       ['RTS was enabled by an experiment']),
      api.post_process(post_process.MustRun, 'RTS was used'),
      api.post_process(post_process.PropertyEquals, 'rts_setting',
                       'rts-chromium'),
      api.post_process(
          post_process.PropertyEquals, '$recipe_engine/cq/output', {
              "reusability": {
                  "modeAllowlist": ["DRY_RUN", "QUICK_DRY_RUN"]
              },
              'reuse': [{
                  'modeRegexp': 'DRY_RUN'
              }, {
                  'modeRegexp': 'QUICK_DRY_RUN'
              }]
          }),
      api.post_process(post_process.PropertyEquals, 'rts_was_used', True),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'rts on dry run experiment reused by quick run',
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
          # This change number will result in a value of 0 compared to the
          # threshold ensuring it runs if any run is capable
          change_number=25,
      ),
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'chromium-rel': {
                  'gtest_tests': [{
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.step_data(
          'find rts command lines (with patch)',
          api.json.output({
              'base_unittests': [
                  './%s' % 'base_unittests', '--fake-without-patch-flag',
                  '--fake-log-file', '$ISOLATED_OUTDIR/fake.log',
                  '-filter=base_unittests.filter'
              ]
          })),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(post_process.MustRun, 'RTS was used'),
      api.post_process(post_process.PropertyEquals, 'rts_setting',
                       'rts-chromium'),
      api.post_process(
          post_process.PropertyEquals, '$recipe_engine/cq/output', {
              "reusability": {
                  "modeAllowlist": ["DRY_RUN", "QUICK_DRY_RUN"]
              },
              'reuse': [{
                  'modeRegexp': 'DRY_RUN'
              }, {
                  'modeRegexp': 'QUICK_DRY_RUN'
              }]
          }),
      api.post_process(post_process.PropertyEquals, 'rts_was_used', True),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'quick run enabled but not used',
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
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'chromium-rel': {
                  'gtest_tests': [{
                      'test': 'base_unittests',
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              },
          }),
      api.post_process(post_process.DoesNotRun, 'RTS was used'),
      api.post_process(post_process.MustRun, 'quick run options'),
      api.post_process(post_process.PropertyEquals, 'rts_setting',
                       'rts-chromium'),
      api.post_process(post_process.PropertiesDoNotContain, 'rts_was_used'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'quick run rts disabled by footer',
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
      api.step_data('parse description',
                    api.json.output({'Disable-Rts': ['true']})),
      api.post_process(post_process.DoesNotRun, 'quick run options'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'depend_on_footer_failure',
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
      ),
      ctbc_api.properties(
          ctbc_api.properties_assembler_for_try_builder().with_mirrored_builder(
              builder_group='fake-group',
              builder='fake-builder',
          ).assemble()),
      api.step_data(
          'parse description',
          api.json.output(
              {tryserver.constants.CQ_DEPEND_FOOTER: 'chromium:123456'})),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.ResultReasonRE,
                       r'Commit message footer Cq-Depend is not supported.*'),
      api.post_process(post_process.DropExpectation),
  )

  builder_db = ctbc.BuilderDatabase.create({
      'fake-group': {
          'fake-builder':
              ctbc.BuilderSpec.create(
                  chromium_config='chromium',
                  gclient_config='chromium',
              ),
      },
      'fake-tester-group': {
          'fake-tester':
              ctbc.BuilderSpec.create(
                  execution_mode=ctbc.TEST,
                  parent_builder_group='fake-group',
                  parent_buildername='fake-builder',
                  chromium_config='chromium',
                  gclient_config='chromium',
              ),
      },
      'fake-unmirrored-tester-group': {
          'fake-unmirrored-tester':
              ctbc.BuilderSpec.create(
                  execution_mode=ctbc.TEST,
                  parent_builder_group='fake-group',
                  parent_buildername='fake-builder',
                  chromium_config='chromium',
                  gclient_config='chromium',
              ),
      },
  })

  yield api.test(
      'unmirrored-tester',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                          tester_group='fake-tester-group',
                          tester='fake-tester',
                      ),
              },
          }),
      ),
      api.post_check(post_process.MustRun,
                     'read test spec (fake-tester-group.json)'),
      api.post_check(post_process.DoesNotRun,
                     'read test spec (fake-unmirrored-tester-group.json)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'unmirrored-tester-include-all-triggered-testers',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                          include_all_triggered_testers=True,
                      ),
              },
          }),
      ),
      api.post_check(post_process.MustRun,
                     'read test spec (fake-tester-group.json)'),
      api.post_check(post_process.MustRun,
                     'read test spec (fake-unmirrored-tester-group.json)'),
      api.post_process(post_process.DropExpectation),
  )

  def _generate_test_result(test_id, test_variant, status=None):
    status = status or test_result_pb2.PASS
    vd = getattr(test_variant, 'def')
    vh = base64.b64encode(
        ('\n'.join('{}:{}'.format(k, v)
                   for k, v in vd.items())).encode('utf-8')).decode('utf-8')
    return test_result_pb2.TestResult(
        test_id=test_id,
        variant=test_variant,
        variant_hash=vh,
        expected=False,
        status=status,
    )

  correct_variant = resultdb_common.Variant()
  variant_def = getattr(correct_variant, 'def')
  variant_def['os'] = 'Mac-11'
  variant_def['test_suite'] = ('ios_chrome_bookmarks_eg2tests_module_iPad '
                               'Air 2 14.4')

  test_id = (
      'ninja://ios/chrome/test/earl_grey2:ios_chrome_bookmarks_eg2tests_module/'
      'TestSuite.test_a')
  inv = 'invocations/1'
  current_patchset_invocations = {
      inv:
          api.resultdb.Invocation(
              test_results=[_generate_test_result(test_id, correct_variant)])
  }

  recent_run = test_history.QueryTestHistoryResponse(
      verdicts=[], next_page_token='dummy_token')

  yield api.test(
      'basic_flakiness',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                          include_all_triggered_testers=True,
                      ),
              },
          }),
      ),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'isolated_scripts': [{
                      "isolate_name":
                          "ios_chrome_bookmarks_eg2tests_module",
                      "name": ("ios_chrome_bookmarks_eg2tests_module_iPad "
                               "Air 2 14.4"),
                      "swarming": {
                          "can_use_on_swarming_builders": True,
                          "dimension_sets": [{
                              "os": "Mac-11"
                          }],
                      },
                      "test_id_prefix":
                          ("ninja://ios/chrome/test/earl_grey2:"
                           "ios_chrome_bookmarks_eg2tests_module/")
                  },],
              },
          }),
      api.flakiness(check_for_flakiness=True,),
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.resultdb.query(
          inv_bundle=current_patchset_invocations,
          step_name=(
              'collect tasks (with patch).'
              'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 results'),
      ),
      api.luci_analysis.query_test_history(
          recent_run,
          ('ninja://ios/chrome/test/earl_grey2:'
           'ios_chrome_bookmarks_eg2tests_module/TestSuite.test_a'),
          parent_step_name='searching_for_new_tests',
      ),
      api.resultdb.query(
          inv_bundle=current_patchset_invocations,
          step_name=(
              'test new tests for flakiness.'
              'collect tasks (check flakiness shard #0).'
              'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 results'),
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  flaky_results = {
      'invocations/100':
          api.resultdb.Invocation(test_results=[
              _generate_test_result(test_id, correct_variant),
              _generate_test_result(
                  test_id, correct_variant, status=test_result_pb2.FAIL)
          ])
  }

  yield api.test(
      'failed_test',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                      ),
              },
          }),
      ),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'isolated_scripts': [{
                      "isolate_name":
                          "ios_chrome_bookmarks_eg2tests_module",
                      "name": ("ios_chrome_bookmarks_eg2tests_module_iPad "
                               "Air 2 14.4"),
                      "swarming": {
                          "can_use_on_swarming_builders": True,
                          "dimension_sets": [{
                              "os": "Mac-11"
                          }],
                      },
                      "test_id_prefix":
                          ("ninja://ios/chrome/test/earl_grey2:"
                           "ios_chrome_bookmarks_eg2tests_module/")
                  },],
              },
          }),
      api.flakiness(check_for_flakiness=True,),
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.resultdb.query(
          inv_bundle=current_patchset_invocations,
          step_name=(
              'collect tasks (with patch).'
              'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 results'),
      ),
      api.luci_analysis.query_test_history(
          recent_run,
          ('ninja://ios/chrome/test/earl_grey2:'
           'ios_chrome_bookmarks_eg2tests_module/TestSuite.test_a'),
          parent_step_name='searching_for_new_tests',
      ),
      api.override_step_data(
          ('test new tests for flakiness.'
           'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(check flakiness shard #0) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.json.output({}), failure=False)),
      api.resultdb.query(
          inv_bundle=flaky_results,
          step_name=(
              'test new tests for flakiness.'
              'collect tasks (check flakiness shard #0).'
              'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 results')),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'invalid_test',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                      ),
              },
          }),
      ),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'isolated_scripts': [{
                      "isolate_name":
                          "ios_chrome_bookmarks_eg2tests_module",
                      "name": ("ios_chrome_bookmarks_eg2tests_module_iPad "
                               "Air 2 14.4"),
                      "swarming": {
                          "can_use_on_swarming_builders": True,
                          "dimension_sets": [{
                              "os": "Mac-11"
                          }],
                      },
                      "test_id_prefix":
                          ("ninja://ios/chrome/test/earl_grey2:"
                           "ios_chrome_bookmarks_eg2tests_module/")
                  },],
              },
          }),
      api.flakiness(check_for_flakiness=True,),
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.resultdb.query(
          inv_bundle=current_patchset_invocations,
          step_name=(
              'collect tasks (with patch).'
              'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 results'),
      ),
      api.luci_analysis.query_test_history(
          recent_run,
          ('ninja://ios/chrome/test/earl_grey2:'
           'ios_chrome_bookmarks_eg2tests_module/TestSuite.test_a'),
          parent_step_name='searching_for_new_tests',
      ),
      api.override_step_data(
          ('test new tests for flakiness.'
           'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(check flakiness shard #0) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.json.output({}), internal_failure=True)),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'cancel-during-checkout',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                      ),
              },
          }),
      ),
      api.step_data(
          'gclient runhooks (with patch)',
          retcode=-15,
          cancel=True,
          global_shutdown_event='after',
      ),
      api.post_check(post_process.DoesNotRunRE, '.+ \(without patch\)'),
      api.post_process(post_process.DropExpectation),
  )

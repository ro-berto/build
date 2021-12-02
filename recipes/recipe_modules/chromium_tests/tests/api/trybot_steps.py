# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64

from recipe_engine import post_process

from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc
from RECIPE_MODULES.build.chromium_tests_builder_config import try_spec
from RECIPE_MODULES.depot_tools.tryserver import api as tryserver

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import common as resultdb_common
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import resultdb as resultdb_pb2

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

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
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
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
        'st-rel':
            ctbc.TrySpec.create(
                mirrors=[
                    ctbc.TryMirror.create(
                        builder_group='chromium.test',
                        buildername='chromium-rel',
                        tester='chromium-rel',
                    ),
                ],
                filter_stable_test=try_spec.QUICK_RUN_ONLY,
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
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
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
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
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
          builder='linux_chromium_clobber_rel_ng',
      ),
  )

  yield api.test(
      'analyze_names',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux',
          builder='fuchsia_x64',
      ),
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
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
  )

  yield api.test(
      'no_compile_no_source',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
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
          }),
          ),
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
      api.filter.suppress_analyze(),
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
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
      api.properties(swarm_hashes={
          'base_unittests': '[dummy hash for base_unittests/size]'
      }),
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
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
      api.properties(swarm_hashes={
          'base_unittests': '[dummy hash for base_unittests/size]'
      }),
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
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
      api.properties(swarm_hashes={
          'base_unittests': '[dummy hash for base_unittests/size]'
      }),
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
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
      multiple_base_unittests_additional_compile_target(),
      api.filter.suppress_analyze(),
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
      api.properties(dry_run=True),
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
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
      'quick run stable filter',
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
          builder='st-rel',
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
          builder_group='tryserver.chromium.linux',
          builder='linux-rel',
      ),
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

  def _generate_build(builder, invocation, build_input=None):
    return build_pb2.Build(
        builder=builder,
        infra=build_pb2.BuildInfra(
            resultdb=build_pb2.BuildInfra.ResultDB(invocation=invocation)),
        input=build_input)

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

  builder = builder_pb2.BuilderID(
      builder='fake-try-builder', project='chromium', bucket='try')
  inv = 'invocations/1'
  build_database = [_generate_build(builder, inv)]
  current_patchset_invocations = {
      inv:
          api.resultdb.Invocation(
              test_results=[_generate_test_result(test_id, correct_variant)])
  }

  recent_run = resultdb_pb2.GetTestResultHistoryResponse(entries=[])

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
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.filter.suppress_analyze(),
      # Search for all past invocations for builder
      api.buildbucket.simulated_search_results(
          builds=build_database,
          step_name='searching_for_new_tests.fetch previously run invocations'),
      api.resultdb.query(
          inv_bundle=current_patchset_invocations,
          step_name=('searching_for_new_tests.'
                     'fetch test variants for current patchset')),
      api.resultdb.get_test_result_history(
          recent_run,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
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
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.filter.suppress_analyze(),
      # Search for all past invocations for builder
      api.buildbucket.simulated_search_results(
          builds=build_database,
          step_name='searching_for_new_tests.fetch previously run invocations'),
      api.resultdb.query(
          inv_bundle=current_patchset_invocations,
          step_name=('searching_for_new_tests.'
                     'fetch test variants for current patchset')),
      api.resultdb.get_test_result_history(
          recent_run,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.override_step_data(
          ('test new tests for flakiness.'
           'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(check flakiness) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.json.output({}), failure=False)),
      api.resultdb.query(
          inv_bundle=flaky_results,
          step_name=(
              'test new tests for flakiness.'
              'collect tasks (check flakiness).'
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
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.filter.suppress_analyze(),
      # Search for all past invocations for builder
      api.buildbucket.simulated_search_results(
          builds=build_database,
          step_name='searching_for_new_tests.fetch previously run invocations'),
      api.resultdb.query(
          inv_bundle=current_patchset_invocations,
          step_name=('searching_for_new_tests.'
                     'fetch test variants for current patchset')),
      api.resultdb.get_test_result_history(
          recent_run,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.override_step_data(
          ('test new tests for flakiness.'
           'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(check flakiness) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.json.output({}), internal_failure=True)),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

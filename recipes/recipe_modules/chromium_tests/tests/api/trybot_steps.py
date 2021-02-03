# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.recipe_api import Property
import textwrap

from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, try_spec
from RECIPE_MODULES.build.rts_chromium.rts_spec import RTSSpec

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
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

_TEST_BUILDERS = bot_db.BotDatabase.create({
    'chromium.test': {
        'staging-chromium-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
                chromium_tests_apply_config=['staging'],
            ),
        'staging-chromium-test-rel':
            bot_spec.BotSpec.create(
                gclient_config='chromium',
                chromium_tests_apply_config=['staging'],
            ),
        'retry-shards':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
            ),
        'retry-shards-test':
            bot_spec.BotSpec.create(
                execution_mode=bot_spec.TEST,
                parent_buildername='retry-shards',
            ),
    },
    'tryserver.chromium.unmirrored': {
        'unmirrored-chromium-rel':
            bot_spec.BotSpec.create(
                chromium_config='chromium',
                gclient_config='chromium',
            ),
    },
})

_TEST_TRYBOTS = try_spec.TryDatabase.create({
    'tryserver.chromium.test': {
        'retry-shards':
            try_spec.TrySpec.create(
                retry_failed_shards=True,
                mirrors=[
                    try_spec.TryMirror.create(
                        builder_group='chromium.test',
                        buildername='retry-shards',
                        tester='retry-shards-test',
                    ),
                ],
            ),
        'staging-chromium-rel':
            try_spec.TrySpec.create(mirrors=[
                try_spec.TryMirror.create(
                    builder_group='chromium.test',
                    buildername='staging-chromium-rel',
                    tester='staging-chromium-test-rel',
                ),
            ]),
        'rts-rel':
            try_spec.TrySpec.create_for_single_mirror(
                builder_group='chromium.test',
                buildername='staging-chromium-rel',
                rts_spec=RTSSpec(
                    rts_chromium_version='latest',
                    model_version='latest',
                    target_change_recall=0.9,
                )),
    }
})


def RunSteps(api):
  assert api.tryserver.is_tryserver
  api.path.mock_add_paths(
      api.profiles.profile_dir().join('overall-merged.profdata'))
  api.path.mock_add_paths(api.profiles.profile_dir().join(
      api.pgo.TEMP_PROFDATA_FILENAME))

  raw_result = api.chromium_tests.trybot_steps()
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
      'rts',
      api.chromium.try_build(
          builder_group='tryserver.chromium.test', builder='rts-rel'),
      api.chromium_tests.builders(_TEST_BUILDERS),
      api.chromium_tests.trybots(_TEST_TRYBOTS),
      api.filter.suppress_analyze(),
      api.post_process(post_process.MustRun,
                       'select tests to skip (rts).rts-chromium select'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'staging',
      api.chromium.try_build(
          builder_group='tryserver.chromium.test',
          builder='staging-chromium-rel'),
      api.chromium_tests.builders(_TEST_BUILDERS),
      api.chromium_tests.trybots(_TEST_TRYBOTS),
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'staging-chromium-test-rel': {
                  'gtest_tests': ['staging_base_unittests'],
              },
          }),
      api.filter.suppress_analyze(),
      api.post_process(post_process.MustRun,
                       'staging_base_unittests (with patch)'),
      api.post_process(post_process.DropExpectation),
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
      api.chromium.try_build(
          builder_group='tryserver.chromium.unmirrored',
          builder='unmirrored-chromium-rel'),
      api.chromium_tests.builders(_TEST_BUILDERS),
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
      api.chromium.try_build(
          builder_group='fake-group', builder='fake-try-builder'),
      api.chromium_tests.trybots(
          try_spec.TryDatabase.create({
              'fake-group': {
                  'fake-try-builder':
                  try_spec.TrySpec.create(mirrors=[
                      try_spec.TryMirror.create(
                          builder_group='fake-group',
                          buildername='fake-builder',
                          tester='fake-dummy-tester',
                      )
                  ]),
              },
          })),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              'fake-group': {
                  'fake-builder':
                  bot_spec.BotSpec.create(
                      chromium_config='chromium',
                      gclient_config='chromium',
                  ),
                  'fake-dummy-tester':
                  bot_spec.BotSpec.create(
                      execution_mode=bot_spec.PROVIDE_TEST_SPEC),
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
      api.chromium.try_build(
          builder_group='tryserver.chromium.test',
          builder='retry-shards',
      ),
      api.chromium_tests.builders(_TEST_BUILDERS),
      api.chromium_tests.trybots(_TEST_TRYBOTS),
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
      api.chromium.try_build(
          builder_group='tryserver.chromium.test', builder='retry-shards'),
      api.chromium_tests.builders(_TEST_BUILDERS),
      api.chromium_tests.trybots(_TEST_TRYBOTS),
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
      api.chromium.try_build(
          builder_group='tryserver.chromium.test', builder='retry-shards'),
      api.chromium_tests.builders(_TEST_BUILDERS),
      api.chromium_tests.trybots(_TEST_TRYBOTS),
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
      api.chromium.try_build(
          builder_group='tryserver.chromium.test', builder='retry-shards'),
      api.chromium_tests.builders(_TEST_BUILDERS),
      api.chromium_tests.trybots(_TEST_TRYBOTS),
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

  fake_group = 'fake_group'
  fake_builder = 'fake-builder'
  fake_test = 'fake_test'
  fake_try_builder = 'fake-try-builder'

  yield api.test(
      'trybot_uploads_isolates_but_does_not_run_tests',
      api.properties(
          config='Release',
          swarm_hashes={fake_test: 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeee'},
      ),
      api.platform('linux', 64),
      api.chromium.try_build(
          builder_group=fake_group, builder=fake_try_builder),
      api.chromium_tests.trybots(
          try_spec.TryDatabase.create({
              fake_group: {
                  fake_try_builder:
                      try_spec.TrySpec.create(mirrors=[
                          try_spec.TryMirror.create(
                              builder_group=fake_group,
                              buildername=fake_builder,
                          )
                      ])
              }
          })),
      api.chromium_tests.builders(
          bot_db.BotDatabase.create({
              fake_group: {
                  fake_builder:
                      bot_spec.BotSpec.create(
                          chromium_config='chromium',
                          gclient_config='chromium',
                          upload_isolates_but_do_not_run_tests=True,
                      ),
              }
          })),
      api.chromium_tests.read_source_side_spec(
          fake_group, {
              fake_builder: {
                  'isolated_scripts': [{
                      'name': fake_test,
                      'swarming': {
                          'can_use_on_swarming_builders': True,
                      }
                  }],
              }
          }),
      api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
              'base': {
                  'exclusions': ['f.*'],
              },
              'chromium': {
                  'exclusions': [],
              }
          })),
      api.post_process(post_process.MustRun, 'isolate tests (with patch)'),
      api.post_process(post_process.MustRun, 'explain isolate tests'),
      api.post_process(post_process.DoesNotRun, 'mark: before_tests'),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'chromium_swarming',
    'chromium_tests',
    'filter',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'test_utils',
]


_TEST_BUILDERS = {
  'chromium.test': {
    'builders': {
      'staging-chromium-rel': {
        'gclient_config': 'chromium',
        'chromium_tests_apply_config': ['staging'],
      },
      'staging-chromium-test-rel': {
        'gclient_config': 'chromium',
        'chromium_tests_apply_config': ['staging'],
      },
      'retry-shards': {
        'chromium_config': 'chromium',
        'gclient_config': 'chromium',
        'retry_failed_shards': True,
      },
      'retry-shards-test': {
        'bot_type': 'tester',
      },
    },
  },
  'tryserver.chromium.unmirrored': {
    'builders': {
      'unmirrored-chromium-rel': {
        'gclient_config': 'chromium',
      },
    },
  },
}

_TEST_TRYBOTS = {
  'tryserver.chromium.test': {
    'builders': {
      'retry-shards': {
        'bot_ids': [
          {
            'mastername': 'chromium.test',
            'buildername': 'retry-shards',
            'tester': 'retry-shards-test',
          },
        ],
      },
      'staging-chromium-rel': {
        'bot_ids': [
          {
            'mastername': 'chromium.test',
            'buildername': 'staging-chromium-rel',
            'tester': 'staging-chromium-test-rel',
          },
        ],
      },
    },
  },
}


def RunSteps(api):
  api.chromium_tests.trybot_steps(
      builders=api.properties.get('builders'),
      trybots=api.properties.get('trybots'))
  assert api.chromium_tests.is_precommit_mode()


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': ['base_unittests'],
              },
          }
      ) +
      api.filter.suppress_analyze()
  )

  yield (
      api.test('staging') +
      api.properties.tryserver(
          mastername='tryserver.chromium.test',
          buildername='staging-chromium-rel',
          builders=_TEST_BUILDERS,
          trybots=_TEST_TRYBOTS,
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'staging-chromium-test-rel': {
                  'gtest_tests': ['staging_base_unittests'],
              },
          }
      ) +
      api.filter.suppress_analyze() +
      api.post_process(post_process.MustRun,
                       'staging_base_unittests (with patch)') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('analyze_compile_mode') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_clobber_rel_ng',
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True)
  )

  yield (
      api.test('analyze_names') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='fuchsia_x64',
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.override_step_data(
          'read filter exclusion spec',
          api.json.output({
            'base': {'exclusions': []},
            'chromium': {'exclusions': []},
            'fuchsia': {'exclusions': ['path/to/fuchsia/exclusion.py']},
          })) +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('path/to/fuchsia/exclusion.py')) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('no_compile') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True)
  )

  yield (
      api.test('no_compile_no_source') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('OWNERS')
      )
  )

  yield (
      api.test('unmirrored') +
      api.properties.tryserver(
          mastername='tryserver.chromium.unmirrored',
          buildername='unmirrored-chromium-rel',
          builders=_TEST_BUILDERS,
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.chromium_tests.read_source_side_spec(
          'tryserver.chromium.unmirrored', {
              'unmirrored-chromium-rel': {
                  'gtest_tests': ['bogus_unittests'],
              },
          }
      ) +
      api.filter.suppress_analyze() +
      api.post_process(post_process.MustRun, 'bogus_unittests (with patch)') +
      api.post_process(post_process.DropExpectation)
  )

  # Check the 5% experiment for exparchive only runs on 5% of builds. It uses
  # the buildnumber to determine when to be enabled. When enabled you get
  # individual isolate steps for each test, when disabled you get a single
  # isolate step for all tests.
  yield (
    api.test('exparchive_5percent_experiment_enabled') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='linux-rel',
        buildnumber=1020, # 5% is (x % 100/5 == 0)
        swarm_hashes={
          'base_unittests':
          '[dummy hash for base_unittests]'
        },
        path_config='kitchen') +
    api.runtime(is_experimental=False, is_luci=True) +
    api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Tests': {
                'gtest_tests': [
                    {
                        'test': 'base_unittests',
                        'swarming': {
                            'can_use_on_swarming_builders': True,
                        }
                    }
                ],
            },
        }
    ) +
    api.filter.suppress_analyze() +
    api.post_process(
        post_process.MustRun, 'isolate tests (with patch)') +
    api.post_process(post_process.DropExpectation)
  )
  for i in range(1, 20):
    yield (
      api.test('exparchive_5percent_experiment_disabled_%i' % i) +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux-rel',
          buildnumber=1020 + i,
          swarm_hashes={
            'base_unittests':
            '[dummy hash for base_unittests]'
          },
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.chromium_tests.read_source_side_spec(
          'chromium.linux', {
              'Linux Tests': {
                  'gtest_tests': [
                      {
                          'test': 'base_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          }
                      }
                  ],
              },
          }
      ) +
      api.filter.suppress_analyze() +
      api.post_process(
          post_process.MustRun, 'isolate tests (with patch)') +
      api.post_process(
          post_process.DoesNotRun, 'isolate base_unittests') +
      api.post_process(post_process.DropExpectation)
    )


  CUSTOM_PROPS = api.properties.tryserver(
      mastername='tryserver.chromium.test',
      buildername='retry-shards',
      builders=_TEST_BUILDERS,
      trybots=_TEST_TRYBOTS,
      swarm_hashes={
        'base_unittests':
        '[dummy hash for base_unittests]'
      },
      path_config='kitchen')

  yield (
      api.test('retry_shards') +
      CUSTOM_PROPS +
      api.runtime(is_experimental=False, is_luci=True) +
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'retry-shards': {
                  'gtest_tests': [
                      {
                          'test': 'base_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          }
                      }
                  ],
              },
          }
      ) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False)) +
      api.filter.suppress_analyze() +
      api.post_process(
          post_process.MustRun, 'base_unittests (retry shards with patch)') +
      api.post_process(
          post_process.DoesNotRun, 'base_unittests (without patch)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('retry_shards_without_patch') +
      CUSTOM_PROPS +
      api.runtime(is_experimental=False, is_luci=True) +
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'retry-shards': {
                  'gtest_tests': [
                      {
                          'test': 'base_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          }
                      }
                  ],
              },
          }
      ) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False)) +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False)) +
      api.override_step_data(
          'base_unittests (without patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False)) +
      api.filter.suppress_analyze() +
      api.post_process(
          post_process.MustRun, 'base_unittests (retry shards with patch)') +
      api.post_process(
          post_process.MustRun, 'base_unittests (without patch)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('retry_shards_invalid') +
      api.properties.tryserver(
          mastername='tryserver.chromium.test',
          buildername='retry-shards',
          builders=_TEST_BUILDERS,
          trybots=_TEST_TRYBOTS,
          swarm_hashes={
            'base_unittests':
            '[dummy hash for base_unittests]'
          },
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'retry-shards': {
                  'gtest_tests': [
                      {
                          'test': 'base_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          }
                      }
                  ],
              },
          }
      ) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.gtest_results('invalid_results', 1)) +
      api.filter.suppress_analyze() +
      api.post_process(
          post_process.MustRun, 'base_unittests (retry shards with patch)') +
      api.post_process(
          post_process.DoesNotRun, 'base_unittests (without patch)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('retry_shards_invalid_retry') +
      api.properties.tryserver(
          mastername='tryserver.chromium.test',
          buildername='retry-shards',
          builders=_TEST_BUILDERS,
          trybots=_TEST_TRYBOTS,
          swarm_hashes={
            'base_unittests':
            '[dummy hash for base_unittests]'
          },
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'retry-shards': {
                  'gtest_tests': [
                      {
                          'test': 'base_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          }
                      }
                  ],
              },
          }
      ) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.canned_gtest_output(False)) +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.gtest_results('invalid results', 1)) +
      api.filter.suppress_analyze() +
      api.post_process(
          post_process.MustRun, 'base_unittests (with patch)') +
      api.post_process(
          post_process.MustRun, 'base_unittests (retry shards with patch)') +
      api.post_process(
          post_process.MustRun, 'base_unittests (without patch)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('retry_shards_all_invalid_results') +
      api.properties.tryserver(
          mastername='tryserver.chromium.test',
          buildername='retry-shards',
          builders=_TEST_BUILDERS,
          trybots=_TEST_TRYBOTS,
          swarm_hashes={
            'base_unittests':
            '[dummy hash for base_unittests]'
          },
          path_config='kitchen') +
      api.runtime(is_experimental=False, is_luci=True) +
      api.chromium_tests.read_source_side_spec(
          'chromium.test', {
              'retry-shards': {
                  'gtest_tests': [
                      {
                          'test': 'base_unittests',
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          }
                      }
                  ],
              },
          }
      ) +
      api.override_step_data(
          'base_unittests (with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.gtest_results('invalid results', 1)) +
      api.override_step_data(
          'base_unittests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(failure=True) +
          api.test_utils.gtest_results('invalid results', 1)) +
      api.filter.suppress_analyze() +
      api.post_process(
          post_process.MustRun, 'base_unittests (with patch)') +
      api.post_process(
          post_process.MustRun, 'base_unittests (retry shards with patch)') +
      api.post_process(
          post_process.MustRun, 'base_unittests (without patch)') +
      api.post_process(post_process.StatusSuccess) +
      api.post_process(post_process.DropExpectation)
  )

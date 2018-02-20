# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_tests',
    'commit_position',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'isolate',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'swarming',
    'test_results',
    'test_utils',
]

from recipe_engine import post_process


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')
  api.test_results.set_config('public_server')

  update_step = api.bot_update.ensure_checkout()

  single_spec = api.properties.get('single_spec')
  test_spec = {
      'test_buildername': {
          'gtest_tests': [single_spec] if single_spec else [],
      }
  }

  for test in api.chromium_tests.steps.generate_gtest(
      api,
      api.chromium_tests,
      'test_mastername',
      'test_buildername',
      test_spec,
      update_step):
    try:
      test.pre_run(api, '')
      test.run(api, '')
      test.post_run(api, '')
    finally:
      api.step('details', [])
      api.step.active_result.presentation.logs['details'] = [
          'compile_targets: %r' % test.compile_targets(api),
          'uses_local_devices: %r' % test.uses_local_devices,
      ]


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'total_shards': 2,
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
      )
  )

  yield (
      api.test('swarming') +
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'dimension_sets': [
                      {
                          'os': 'Linux',
                      },
                  ],
                  'cipd_packages': [
                      {
                          'location': '{$HOME}/logdog',
                          'cipd_package': 'infra/logdog/linux-386',
                          'revision': 'git_revision:deadbeef',
                      },
                  ],
              },
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      )
  )

  yield (
      api.test('merge') +
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'merge': {
                  'script': '//merge_script.py',
              },
              'swarming': {
                'can_use_on_swarming_builders': True,
              },
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      )
  )

  yield (
      api.test('merge_invalid') +
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'merge': {
                  'script': 'merge_script.py',
              },
              'swarming': {
                'can_use_on_swarming_builders': True,
              },
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      )
  )

  yield (
      api.test('set_up and tear down') +
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'setup': [
                {
                  'script': '//set_up_script1.py',
                },
                {
                  'script': '//set_up_script2.py',
                }
              ],
              'teardown': [
                {
                  'script': '//tear_down_script1.py',
                },
                {
                  'script': '//tear_down_script2.py',
                }
              ],
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
      )
  )

  yield (
      api.test('invalid set_up') +
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'setup': [
                {
                  'script': '//set_up_script1.py',
                },
                {
                  'script': 'set_up_script2.py',
                }
              ],
              'teardown': [
                {
                  'script': '//tear_down_script1.py',
                },
                {
                  'script': '//tear_down_script2.py',
                }
              ],
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
      )
  )

  yield (
      api.test('invalid tear down') +
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'setup': [
                {
                  'script': '//set_up_script1.py',
                },
                {
                  'script': '//set_up_script2.py',
                }
              ],
              'teardown': [
                {
                  'script': '//tear_down_script1.py',
                },
                {
                  'script': 'tear_down_script2.py',
                }
              ],
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
      )
  )

  yield (
      api.test('trigger_script') +
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'trigger_script': {
                  'script': '//trigger_script.py',
              },
              'swarming': {
                'can_use_on_swarming_builders': True,
              },
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      )
  )

  yield (
      api.test('trigger_script_invalid') +
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'trigger_script': {
                  'script': 'trigger_script.py',
              },
              'swarming': {
                'can_use_on_swarming_builders': True,
              },
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      )
  )

  yield (
      api.test('experimental') +
      api.properties(
          single_spec={
              'experiment_percentage': '100',
              'swarming': {
                  'can_use_on_swarming_builders': True,
              },
              'test': 'base_unittests',
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.step_data('base_unittests (experimental)', retcode=1) +
      api.post_process(post_process.StatusCodeIn, 0) +
      api.post_process(post_process.DropExpectation)
  )

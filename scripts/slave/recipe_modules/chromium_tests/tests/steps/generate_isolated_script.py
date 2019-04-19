# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'build',
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'depot_tools/bot_update',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/commit_position',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]

from recipe_engine import post_process


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')

  api.chromium_tests.set_precommit_mode()

  update_step = api.bot_update.ensure_checkout()

  single_spec = api.properties.get('single_spec')
  test_spec = {
      'test_buildername': {
          'isolated_scripts': [single_spec] if single_spec else [],
      }
  }

  for test in api.chromium_tests._generators.generate_isolated_script(
      api,
      api.chromium_tests,
      'test_mastername',
      'test_buildername',
      test_spec,
      update_step):
    try:
      test.pre_run(api, '')
      test.run(api, '')
    finally:
      api.step('details', [])
      api.step.active_result.presentation.logs['details'] = [
          'compile_targets: %r' % test.compile_targets(),
          'uses_local_devices: %r' % test.uses_local_devices,
      ]


def GenTests(api):
  # FIXME: These tests should use the post_process.Filter methods to pick which
  # specific steps are important to the particular test.

  yield (
      api.test('basic') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
      },
      swarm_hashes={
        'base_unittests_run': 'ffffffffffffffffffffffffffffffffffffffff',
      })
  )

  yield (
      api.test('invalid_test_results') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
      },
      swarm_hashes={
        'base_unittests_run': 'ffffffffffffffffffffffffffffffffffffffff',
      }) +
      api.override_step_data('base_unittests', api.json.output({
          'valid': False,
          'failures': [],
      }))
  )

  yield (
      api.test('fake_results_handler') +
      api.properties(
          single_spec={
              'name': 'base_unittests',
              'isolate_name': 'base_unittests_run',
              'results_handler': 'fake',
              'swarming': {
                  'can_use_on_swarming_builders': True,
              },
          },
          swarm_hashes={
            'base_unittests_run': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      )
  )

  yield (
      api.test('swarming') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'merge': {
              'script': '//path/to/script.py',
          },
          'setup': [
            {'script': '//path/to/setup1.py'},
            {'script': '//path/to/setup2.py'}
          ],
          'teardown': [
            {'script': '//path/to/teardown1.py'},
            {'script': '//path/to/teardown2.py'}
          ],
          'swarming': {
              'can_use_on_swarming_builders': True,
          },
        }, swarm_hashes={
            'base_unittests_run': 'deadbeef',
        },
        mastername='test_mastername',
        buildername='test_buildername',
        buildnumber=1)
  )

  yield (
      api.test('service_account') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'swarming': {
              'can_use_on_swarming_builders': True,
              'service_account': 'test-account@serviceaccount.com',
          },
        }, swarm_hashes={
            'base_unittests_run': 'deadbeef',
        },
        mastername='test_mastername',
        buildername='test_buildername',
        buildnumber=1) +
      api.post_process(post_process.StepCommandContains,
          '[trigger] base_unittests', [
              '--service-account', 'test-account@serviceaccount.com']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('bad set up') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'merge': {
              'script': '//path/to/script.py',
          },
          'teardown': [
            {'script': '//path/to/teardown1.py'},
            {'script': 'path/to/teardown2.py'}
          ],
          'swarming': {
              'can_use_on_swarming_builders': True,
          },
        }, swarm_hashes={
            'base_unittests_run': 'deadbeef',
        },
        mastername='test_mastername',
        buildername='test_buildername',
        buildnumber=1)
  )

  yield (
      api.test('bad tear down') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'merge': {
              'script': '//path/to/script.py',
          },
          'setup': [
            {'script': '//path/to/setup1.py'},
            {'script': 'path/to/setup2.py'}
          ],
          'swarming': {
              'can_use_on_swarming_builders': True,
          },
        }, swarm_hashes={
            'base_unittests_run': 'deadbeef',
        },
        mastername='test_mastername',
        buildername='test_buildername',
        buildnumber=1)
  )

  yield (
      api.test('swarming_trigger_script') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'trigger_script': {
              'script': '//path/to/script.py',
          },
          'swarming': {
              'can_use_on_swarming_builders': True,
          },
      }, swarm_hashes={
          'base_unittests_run': 'deadbeef',
      },
         mastername='test_mastername',
         buildername='test_buildername',
         buildnumber=1)
  )

  yield (
      api.test('swarming_trigger_script_invalid') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'trigger_script': {
              'script': 'bad',
          },
          'swarming': {
              'can_use_on_swarming_builders': True,
          },
      }, swarm_hashes={
          'base_unittests_run': 'deadbeef',
      },
         mastername='test_mastername',
         buildername='test_buildername',
         buildnumber=1)
  )

  yield (
      api.test('swarming_dimension_sets') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'swarming': {
              'can_use_on_swarming_builders': True,
              'dimension_sets': [
                  {'os': 'Linux'},
              ],
          },
      }, swarm_hashes={
            'base_unittests_run': 'ffffffffffffffffffffffffffffffffffffffff',
      },
      mastername='test_mastername',
      buildername='test_buildername',
      buildnumber=1)
  )

  yield (
      api.test('swarming_dimension_sets_plus_optional') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'swarming': {
              'can_use_on_swarming_builders': True,
              'dimension_sets': [
                  {'os': 'Linux'},
              ],
              'optional_dimensions': {
                  60: [{'os': 'Ubuntu-14.04'}],
              },
          },
      }, swarm_hashes={
            'base_unittests_run': 'ffffffffffffffffffffffffffffffffffffffff',
      },
      mastername='test_mastername',
      buildername='test_buildername',
      buildnumber=1)
  )

  yield (
      api.test('spec_error') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'results_handler': 'bogus',
      })
  )

  yield (
      api.test('merge_invalid') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'merge': {
              'script': 'path/to/script.py',
          },
          'swarming': {
              'can_use_on_swarming_builders': True,
          },
      })
  )

  yield (
      api.test('precommit_args') +
      api.properties(single_spec={
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
          'args': [
              '--should-be-in-output',
          ],
          'precommit_args': [
              '--should-also-be-in-output',
          ],
      }, swarm_hashes={
            'base_unittests_run': 'ffffffffffffffffffffffffffffffffffffffff',
      })
  )

  yield (
      api.test('blink_web_tests_with_suffixes') +
      api.properties(
          single_spec={
              'name': 'blink_web_tests',
              'isolate_name': 'webkit_tests',
              'results_handler': 'layout tests',
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'dimension_sets': [{
                      'os': 'Mac',
                      'gpu': '8086:blah',
                  }],
              },
          },
          swarm_hashes={
            'webkit_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=1
      ) + api.post_process(post_process.Filter(
          # Ensure that we still pass the full step name to the test result
          # upload, but we pass a simplified step name to 'archive results'.
          'Upload to test-results [blink_web_tests on Intel GPU on Mac]',
          'archive results for blink_web_tests', '$result'))
  )

  yield (
      api.test('custom_webkit_tests_step_name') +
      api.properties(
          single_spec={
              'name': 'custom_webkit_tests',
              'isolate_name': 'webkit_tests',
              'results_handler': 'layout tests',
              'swarming': {
                  'can_use_on_swarming_builders': True,
              },
          },
          swarm_hashes={
            'webkit_tests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=1
      )
  )

  yield (
      api.test('swarming_cipd_packages') +
      api.properties(
          single_spec={
              'name': 'base_unittests',
              'isolate_name': 'base_unittests_run',
              'trigger_script': {
                  'script': '//path/to/script.py',
              },
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'cipd_packages': [{
                      'cipd_package': 'cipd/package/name',
                      'location': '../../cipd/package/location',
                      'revision': 'version:1.0',
                   }],
              },
          },
          swarm_hashes={
              'base_unittests_run': 'deadbeef',
          },
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=1
      ) +
      api.post_process(post_process.StepCommandContains,
          '[trigger] base_unittests',
          [
              '--cipd-package',
              '../../cipd/package/location:cipd/package/name:version:1.0',
          ]
      ) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('experimental') +
      api.properties(single_spec={
          'experiment_percentage': '100',
          'name': 'base_unittests',
          'isolate_name': 'base_unittests_run',
      },
      swarm_hashes={
        'base_unittests_run': 'ffffffffffffffffffffffffffffffffffffffff',
      }) +
    api.step_data('base_unittests', retcode=1) +
    api.post_process(post_process.StatusSuccess) +
    api.post_process(post_process.DropExpectation))

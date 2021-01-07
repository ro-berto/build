# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'builder_group',
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
    'recipe_engine/resultdb',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'test_results',
    'test_utils',
]

from recipe_engine import post_process

from RECIPE_MODULES.build.chromium_tests import generators


def RunSteps(api):
  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium')
  api.chromium_swarming.path_to_merge_scripts = (
      api.path['cache'].join('merge_scripts'))
  api.chromium_swarming.set_default_dimension('pool', 'foo')
  api.test_results.set_config('public_server')

  update_step = api.bot_update.ensure_checkout()

  single_spec = api.properties.get('single_spec')
  source_side_spec = {
      'test_buildername': {
          'gtest_tests': [single_spec] if single_spec else [],
      }
  }

  for test_spec in generators.generate_gtests(api, api.chromium_tests,
                                              'test_group', 'test_buildername',
                                              source_side_spec, update_step):
    test = test_spec.get_test()
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
  yield api.test(
      'basic',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
          experiments={'chromium.resultdb.result_sink.gtests_local': True},
      ),
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'total_shards': 2,
          },),
  )

  yield api.test(
      'swarming',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'test_target': '//base:base_unittests',
              'swarming': {
                  'can_use_on_swarming_builders':
                      True,
                  'dimension_sets': [{
                      'os': 'Linux',
                      'foo': None,
                  },],
                  'optional_dimensions': {
                      '60': {
                          'bar': 'baz',
                      },
                  },
                  'cipd_packages': [{
                      'location': '{$HOME}/logdog',
                      'cipd_package': 'infra/logdog/linux-386',
                      'revision': 'git_revision:deadbeef',
                  },],
              },
          },
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
  )

  yield api.test(
      'swarming_with_legacy_optional_dimensions',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'test_target': '//base:base_unittests',
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'dimension_sets': [{
                      'os': 'Linux',
                      'foo': None,
                  },],
                  'optional_dimensions': {
                      '60': [{
                          'bar': 'baz',
                      }],
                  },
              },
          },
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
  )

  yield api.test(
      'use_isolated_scripts_api_in_gtest',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'use_isolated_scripts_api': True,
          },
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.post_process(post_process.StepCommandContains, 'base_unittests',
                       ['--isolated-script-test-output']),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'do_not_use_isolated_scripts_api_in_gtest',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'use_isolated_scripts_api': False,
          },
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.post_process(post_process.StepCommandContains, 'base_unittests',
                       ['--test-launcher-summary-output']),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'service_account',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'service_account': 'test-account@serviceaccount.com',
              },
          },
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.post_check(
          api.swarming.check_triggered_request,
          '[trigger] base_unittests', lambda check, req: check(
              req.service_account == 'test-account@serviceaccount.com')),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'swarming_plus_optional_dimension',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'swarming': {
                  'can_use_on_swarming_builders':
                      True,
                  'dimension_sets': [{
                      'os': 'Linux',
                  },],
                  'cipd_packages': [{
                      'location': '{$HOME}/logdog',
                      'cipd_package': 'infra/logdog/linux-386',
                      'revision': 'git_revision:deadbeef',
                  },],
              },
          },
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
  )

  yield api.test(
      'swarming_with_named_caches',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'swarming': {
                  'can_use_on_swarming_builders':
                      True,
                  'dimension_sets': [{
                      'os': 'Linux',
                  },],
                  'named_caches': [{
                      'name': 'cache_name',
                      'path': '.path/to/named/cache',
                  },]
              },
          },
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.post_check(
          api.swarming.check_triggered_request,
          '[trigger] base_unittests',
          lambda check, req: check(req[0].named_caches['cache_name'] ==
                                   '.path/to/named/cache'),
      ), api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'merge',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
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
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
  )

  yield api.test(
      'merge_invalid',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
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
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
  )

  yield api.test(
      'set_up and tear down',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test':
                  'base_unittests',
              'setup': [{
                  'name': 'setup1',
                  'script': '//set_up_script1.py',
              }, {
                  'name': 'setup2',
                  'script': '//set_up_script2.py',
              }],
              'teardown': [{
                  'name': 'teardown1',
                  'script': '//tear_down_script1.py',
              }, {
                  'name': 'teardown2',
                  'script': '//tear_down_script2.py',
              }],
          },),
  )

  yield api.test(
      'invalid set_up',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test':
                  'base_unittests',
              'setup': [{
                  'name': 'setup1',
                  'script': '//set_up_script1.py',
              }, {
                  'name': 'setup2',
                  'script': 'set_up_script2.py',
              }],
              'teardown': [{
                  'name': 'teardown1',
                  'script': '//tear_down_script1.py',
              }, {
                  'name': 'teardown2',
                  'script': '//tear_down_script2.py',
              }],
          },),
  )

  yield api.test(
      'invalid tear down',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test':
                  'base_unittests',
              'setup': [{
                  'name': 'setup1',
                  'script': '//set_up_script1.py',
              }, {
                  'name': 'setup2',
                  'script': '//set_up_script2.py',
              }],
              'teardown': [{
                  'name': 'teardown1',
                  'script': '//tear_down_script1.py',
              }, {
                  'name': 'teardown2',
                  'script': 'tear_down_script2.py',
              }],
          },),
  )

  yield api.test(
      'trigger_script',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
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
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
  )

  yield api.test(
      'trigger_script_simultaneous_shard_dispatch',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'trigger_script': {
                  'script': '//perf_device_trigger.py',
                  'requires_simultaneous_shard_dispatch': True,
              },
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'shards': 5,
              },
          },
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.post_process(
          post_process.Filter(
              '[trigger (custom trigger script)] base_unittests')),
  )

  yield api.test(
      'trigger_script_invalid',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
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
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
  )

  yield api.test(
      'experimental',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'experiment_percentage': '100',
              'swarming': {
                  'can_use_on_swarming_builders': True,
              },
              'test': 'base_unittests',
          },
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.override_step_data(
          'base_unittests (experimental)',
          api.chromium_swarming.canned_summary_output(None, retcode=1)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )


  def NotIdempotent(check, step_odict, step):
    check('Idempotent flag unexpected',
          '--idempotent' not in step_odict[step].cmd)

  yield api.test(
      'not_idempotent',
      api.chromium.ci_build(
          builder_group='test_group',
          builder='test_buildername',
      ),
      api.properties(
          single_spec={
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'idempotent': False,
              },
              'test': 'base_unittests',
          },
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.post_process(post_process.StatusSuccess),
      api.post_process(NotIdempotent, '[trigger] base_unittests'),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
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

from RECIPE_MODULES.build.chromium_tests import generators


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

  for test in generators.generate_gtest(api, api.chromium_tests,
                                        'test_mastername', 'test_buildername',
                                        test_spec, update_step):
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
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'total_shards': 2,
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'swarming',
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
          mastername='test_mastername',
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'service_account',
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'service_account': 'test-account@serviceaccount.com',
              },
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
      api.post_process(post_process.StepCommandContains,
                       '[trigger] base_unittests', [
                           '--service-account',
                           'test-account@serviceaccount.com',
                       ]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'swarming_plus_optional_dimension',
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'swarming': {
                  'can_use_on_swarming_builders':
                      True,
                  'dimension_sets': [{
                      'os': 'Linux',
                  },],
                  'optional_dimensions': {
                      60: [{
                          'os': 'Ubuntu-14.04'
                      }],
                  },
                  'cipd_packages': [{
                      'location': '{$HOME}/logdog',
                      'cipd_package': 'infra/logdog/linux-386',
                      'revision': 'git_revision:deadbeef',
                  },],
              },
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'swarming_with_named_caches',
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
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
          mastername='test_mastername',
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.post_process(post_process.StepCommandContains,
                       '[trigger] base_unittests',
                       ['--named-cache', 'cache_name', '.path/to/named/cache']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation))

  yield api.test(
      'merge',
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
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'merge_invalid',
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
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'set_up and tear down',
      api.properties(
          single_spec={
              'test':
                  'base_unittests',
              'setup': [{
                  'script': '//set_up_script1.py',
              }, {
                  'script': '//set_up_script2.py',
              }],
              'teardown': [{
                  'script': '//tear_down_script1.py',
              }, {
                  'script': '//tear_down_script2.py',
              }],
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'invalid set_up',
      api.properties(
          single_spec={
              'test':
                  'base_unittests',
              'setup': [{
                  'script': '//set_up_script1.py',
              }, {
                  'script': 'set_up_script2.py',
              }],
              'teardown': [{
                  'script': '//tear_down_script1.py',
              }, {
                  'script': '//tear_down_script2.py',
              }],
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'invalid tear down',
      api.properties(
          single_spec={
              'test':
                  'base_unittests',
              'setup': [{
                  'script': '//set_up_script1.py',
              }, {
                  'script': '//set_up_script2.py',
              }],
              'teardown': [{
                  'script': '//tear_down_script1.py',
              }, {
                  'script': 'tear_down_script2.py',
              }],
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'trigger_script',
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
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'trigger_script_simultaneous_shard_dispatch',
      api.properties(
          single_spec={
              'test': 'base_unittests',
              'trigger_script': {
                  'script': '//perf_device_trigger.py',
                  'requires_simultaneous_shard_dispatch': True,
              },
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'shards': 5
              },
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
      api.post_process(post_process.Filter('[trigger] base_unittests')),
  )

  yield api.test(
      'trigger_script_invalid',
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
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          },
      ),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
  )

  yield api.test(
      'experimental',
      api.properties(
          single_spec={
              'experiment_percentage': '100',
              'swarming': {
                  'can_use_on_swarming_builders': True,
              },
              'test': 'base_unittests',
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
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
      api.properties(
          single_spec={
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'idempotent': False,
              },
              'test': 'base_unittests',
          },
          mastername='test_mastername',
          bot_id='test_bot_id',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }),
      api.buildbucket.ci_build(
          project='chromium',
          git_repo='https://chromium.googlesource.com/chromium/src',
          builder='test_buildername',
          build_number=123,
      ),
      api.post_process(post_process.StatusSuccess),
      api.post_process(NotIdempotent, '[trigger] base_unittests'),
      api.post_process(post_process.DropExpectation),
  )

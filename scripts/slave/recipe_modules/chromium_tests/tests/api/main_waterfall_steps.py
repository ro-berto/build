# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import itertools
import json

from recipe_engine import post_process

DEPS = [
    'chromium_tests',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/runtime',
    'swarming',
]

CUSTOM_BUILDERS = {
  'chromium.example': {
    'settings': {
      'build_gs_bucket': 'chromium-example-archive',
    },
    'builders': {
      'Isolated Transfer Builder': {
        'bot_type': 'builder',
        'chromium_apply_config': ['mb'],
        'chromium_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_tests_apply_config': ['staging'],
        'gclient_config': 'chromium',
        'test_results_config': 'staging_server',
        'testing': {
          'platform': 'linux',
        },
      },
      'Isolated Transfer Tester': {
        'bot_type': 'tester',
        'chromium_apply_config': ['mb'],
        'chromium_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_tests_apply_config': ['staging'],
        'gclient_config': 'chromium',
        'parent_buildername': 'Isolated Transfer Builder',
        'test_results_config': 'staging_server',
        'testing': {
          'platform': 'linux',
        },
      },

      'Isolated Transfer: mixed builder, isolated tester (builder)': {
        'bot_type': 'builder',
        'chromium_apply_config': ['mb'],
        'chromium_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_tests_apply_config': ['staging'],
        'gclient_config': 'chromium',
        'test_results_config': 'staging_server',
        'testing': {
          'platform': 'linux',
        },
      },
      'Isolated Transfer: mixed builder, isolated tester (tester)': {
        'bot_type': 'tester',
        'chromium_apply_config': ['mb'],
        'chromium_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_tests_apply_config': ['staging'],
        'gclient_config': 'chromium',
        'parent_buildername':
          'Isolated Transfer: mixed builder, isolated tester (builder)',
        'test_results_config': 'staging_server',
        'testing': {
          'platform': 'linux',
        },
      },

      'Packaged Transfer Builder': {
        'bot_type': 'builder',
        'chromium_apply_config': ['mb'],
        'chromium_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'gclient_config': 'chromium',
        'testing': {
          'platform': 'linux',
        },
      },
      'Packaged Transfer Tester': {
        'bot_type': 'tester',
        'chromium_apply_config': ['mb'],
        'chromium_config': 'chromium',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'gclient_config': 'chromium',
        'parent_buildername': 'Packaged Transfer Builder',
        'testing': {
          'platform': 'linux',
        },
      },

      'Multiple Triggers: Builder': {
        'android_config': 'main_builder',
        'bot_type': 'builder',
        'chromium_apply_config': ['mb'],
        'chromium_config': 'android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'gclient_apply_config': ['android'],
        'gclient_config': 'chromium',
        'testing': {
          'platform': 'linux',
        },
      },
      'Multiple Triggers: Mixed': {
        'android_config': 'main_builder',
        'bot_type': 'tester',
        'chromium_apply_config': ['mb'],
        'chromium_config': 'android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'gclient_apply_config': ['android'],
        'gclient_config': 'chromium',
        'parent_buildername': 'Multiple Triggers: Builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Multiple Triggers: Isolated': {
        'android_config': 'main_builder',
        'bot_type': 'tester',
        'chromium_apply_config': ['mb'],
        'chromium_config': 'android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_PLATFORM': 'android',
        },
        'gclient_apply_config': ['android'],
        'gclient_config': 'chromium',
        'parent_buildername': 'Multiple Triggers: Builder',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
}


def RunSteps(api):
  bot_config = None
  if api.properties.get('custom_bot_config'):
    bot_config = api.chromium_tests.create_bot_config_object(
        [api.chromium_tests.create_bot_id(
            api.properties['mastername'], api.properties['buildername'])],
        builders=CUSTOM_BUILDERS)
  api.chromium_tests.main_waterfall_steps(bot_config=bot_config)


def GenTests(api):
  yield (
      api.test('builder') +
      api.chromium_tests.platform([{
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder'}]) +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Builder') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.override_step_data('trigger', stdout=api.raw_io.output_text("""
        {
          "builds":[{
           "status": "SCHEDULED",
           "created_ts": "1459200369835900",
           "bucket": "user.username",
           "result_details_json": "null",
           "status_changed_ts": "1459200369835930",
           "created_by": "user:username@example.com",
           "updated_ts": "1459200369835940",
           "utcnow_ts": "1459200369962370",
           "parameters_json": "{\\"This_has_been\\": \\"removed\\"}",
           "id": "9016911228971028736"
          }],
          "kind": "buildbucket#resourcesItem",
          "etag": "\\"8uCIh8TRuYs4vPN3iWmly9SJMqw\\""
        }
      """))
  )

  yield (
      api.test('builder_on_buildbot') +
      api.chromium_tests.platform([{
          'mastername': 'chromium.linux',
          'buildername': 'Linux Builder'}]) +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Builder')
  )

  yield (
      api.test('tester') +
      api.chromium_tests.platform([{
          'mastername': 'chromium.linux',
          'buildername': 'Linux Tests'}]) +
      api.properties.generic(
          mastername='chromium.linux',
          buildername='Linux Tests',
          parent_buildername='Linux Builder') +
      api.override_step_data(
          'read test spec (chromium.linux.json)',
          api.json.output({
              'Linux Tests': {
                  'gtest_tests': ['base_unittests'],
              },
          })
      )
  )

  def TriggersBuilderWithProperties(check, step_odict, builder='', properties=None):
    trigger_step = step_odict['trigger']
    check(
        'TriggersBuilderWithProperties only supports LUCI builds.',
        'trigger_specs' not in trigger_step)
    check(
        '"trigger" step did not run expected command.',
        'cmd' in trigger_step and
        'scheduler.Scheduler.EmitTriggers' in trigger_step['cmd'] and
        'stdin' in trigger_step)
    trigger_json = json.loads(trigger_step['stdin'])

    for batch in trigger_json.get('batches', []):
      if any(builder == j.get('job') for j in batch.get('jobs', [])):
        actual_properties = (
            batch.get('trigger', {}).get('buildbucket', {}).get('properties', {}))
        check(all(p in actual_properties for p in properties))
        break
    else:  # pragma: no cover
      check('"%s" not triggered' % builder, False)

  yield (
      api.test('isolate_transfer_builder') +
      api.properties(
          bot_id='isolated_transfer_builder_id',
          buildername='Isolated Transfer Builder',
          buildnumber=123,
          custom_bot_config=True,
          mastername='chromium.example') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.override_step_data(
          'read test spec (chromium.example.json)',
          api.json.output({
              'Isolated Transfer Tester': {
                  'gtest_tests': [
                      {
                          'args': ['--sample-argument'],
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          },
                          'test': 'base_unittests',
                      },
                  ],
              },
          })
      ) +
      api.post_process(post_process.DoesNotRun, 'package build') +
      api.post_process(
          TriggersBuilderWithProperties,
          builder='Isolated Transfer Tester',
          properties=['swarm_hashes']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('isolate_transfer_tester') +
      api.properties(
          bot_id='isolated_transfer_tester_id',
          buildername='Isolated Transfer Tester',
          buildnumber=123,
          custom_bot_config=True,
          mastername='chromium.example',
          parent_buildername='Isolated Transfer Builder',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.runtime(is_luci=True, is_experimental=False) +
      api.override_step_data(
          'read test spec (chromium.example.json)',
          api.json.output({
              'Isolated Transfer Tester': {
                  'gtest_tests': [
                      {
                          'args': ['--sample-argument'],
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          },
                          'test': 'base_unittests',
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'find isolated tests',
          api.json.output({})
      ) +
      api.post_process(post_process.DoesNotRun, 'extract build') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('isolated_transfer__mixed_builder_isolated_tester') +
      api.properties(
          bot_id='isolated_transfer_builder_id',
          buildername='Isolated Transfer: mixed builder, isolated tester (builder)',
          buildnumber=123,
          custom_bot_config=True,
          mastername='chromium.example') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.override_step_data(
          'read test spec (chromium.example.json)',
          api.json.output({
              'Isolated Transfer: mixed builder, isolated tester (builder)': {
                  'scripts': [
                      {
                          'name': 'check_network_annotations',
                          'script': 'check_network_annotations.py',
                      },
                  ],
              },
              'Isolated Transfer: mixed builder, isolated tester (tester)': {
                  'gtest_tests': [
                      {
                          'args': ['--sample-argument'],
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          },
                          'test': 'base_unittests',
                      },
                  ],
              },
          })
      ) +
      api.post_process(post_process.DoesNotRun, 'package build') +
      api.post_process(
          TriggersBuilderWithProperties,
          builder='Isolated Transfer: mixed builder, isolated tester (tester)',
          properties=['swarm_hashes']) +
      api.post_process(post_process.DropExpectation)
  )

  def TriggersBuilderWithoutProperties(check, step_odict, builder='', properties=None):
    trigger_specs = step_odict['trigger']['trigger_specs']
    for t in trigger_specs:
      if t['builder_name'] == builder:
        check(all(p not in t['properties'] for p in properties))
        return step_odict
    else:  # pragma: no cover
      check('"%s" not triggered' % builder, False)

  yield (
      api.test('isolate_transfer_builder_buildbot') +
      api.properties(
          bot_id='isolated_transfer_builder_id',
          buildername='Isolated Transfer Builder',
          buildnumber=123,
          custom_bot_config=True,
          mastername='chromium.example') +
      api.runtime(is_luci=False, is_experimental=False) +
      api.override_step_data(
          'read test spec (chromium.example.json)',
          api.json.output({
              'Isolated Transfer Tester': {
                  'gtest_tests': [
                      {
                          'args': ['--sample-argument'],
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          },
                          'test': 'base_unittests',
                      },
                  ],
              },
          })
      ) +
      api.post_process(post_process.MustRun, 'package build') +
      api.post_process(
          TriggersBuilderWithoutProperties,
          builder='Isolated Transfer Tester',
          properties=['swarm_hashes']) +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('isolate_transfer_tester_buildbot') +
      api.properties(
          bot_id='isolated_transfer_tester_id',
          buildername='Isolated Transfer Tester',
          buildnumber=123,
          custom_bot_config=True,
          mastername='chromium.example',
          parent_buildername='Isolated Transfer Builder',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.runtime(is_luci=False, is_experimental=False) +
      api.override_step_data(
          'read test spec (chromium.example.json)',
          api.json.output({
              'Isolated Transfer Tester': {
                  'gtest_tests': [
                      {
                          'args': ['--sample-argument'],
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          },
                          'test': 'base_unittests',
                      },
                  ],
              },
          })
      ) +
      api.override_step_data(
          'find isolated tests',
          api.json.output({})
      ) +
      api.post_process(post_process.MustRun, 'extract build') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('package_transfer_builder') +
      api.properties(
          bot_id='packaged_transfer_builder_id',
          buildername='Packaged Transfer Builder',
          buildnumber=123,
          custom_bot_config=True,
          mastername='chromium.example') +
      api.override_step_data(
          'read test spec (chromium.example.json)',
          api.json.output({
              'Packaged Transfer Tester': {
                  'gtest_tests': [
                      {
                          'args': ['--sample-argument'],
                          'swarming': {
                              'can_use_on_swarming_builders': False,
                          },
                          'test': 'base_unittests',
                      },
                  ],
              },
          })
      ) +
      api.post_process(post_process.MustRun, 'package build') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('package_transfer_tester') +
      api.properties(
          bot_id='packaged_transfer_tester_id',
          buildername='Packaged Transfer Tester',
          buildnumber=123,
          custom_bot_config=True,
          mastername='chromium.example',
          parent_buildername='Packaged Transfer Builder',
          swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
      api.override_step_data(
          'read test spec (chromium.example.json)',
          api.json.output({
              'Packaged Transfer Tester': {
                  'gtest_tests': [
                      {
                          'args': ['--sample-argument'],
                          'swarming': {
                              'can_use_on_swarming_builders': False,
                          },
                          'test': 'base_unittests',
                      },
                  ],
              },
          })
      ) +
      api.post_process(post_process.MustRun, 'extract build') +
      api.post_process(post_process.DropExpectation)
  )

  yield (
      api.test('multiple_triggers') +
      api.properties(
          bot_id='multiple_triggers_builder_id',
          buildername='Multiple Triggers: Builder',
          buildnumber=123,
          custom_bot_config=True,
          mastername='chromium.example') +
      api.runtime(is_luci=True, is_experimental=False) +
      api.override_step_data(
          'read test spec (chromium.example.json)',
          api.json.output({
              'Multiple Triggers: Mixed': {
                  'gtest_tests': [
                      {
                          'args': ['--sample-argument'],
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          },
                          'test': 'base_unittests',
                      },
                  ],
                  'junit_tests': [
                      {
                          'test': 'base_junit_tests',
                      },
                  ],
              },
              'Multiple Triggers: Isolated': {
                  'gtest_tests': [
                      {
                          'args': ['--sample-argument'],
                          'swarming': {
                              'can_use_on_swarming_builders': True,
                          },
                          'test': 'base_unittests',
                      },
                  ],
              },
          })
      ) +
      api.post_process(post_process.MustRun, 'package build') +
      api.post_process(
          TriggersBuilderWithProperties,
          builder='Multiple Triggers: Mixed',
          properties=['swarm_hashes']) +
      api.post_process(post_process.DropExpectation)
  )

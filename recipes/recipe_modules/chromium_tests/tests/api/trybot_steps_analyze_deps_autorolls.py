# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from RECIPE_MODULES.build.chromium_tests import bot_db, bot_spec, try_spec

DEPS = [
    'chromium',
    'chromium_tests',
    'chromium_swarming',
    'depot_tools/tryserver',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
    'test_utils',
]



def RunSteps(api):
  assert api.tryserver.is_tryserver
  raw_result = api.chromium_tests.trybot_steps()
  return raw_result


def GenTests(api):

  def deps_exclusion_spec():
    return api.json.output({
        'base': {
            'exclusions': ['DEPS']
        },
        'chromium': {
            'exclusions': []
        },
        'fuchsia': {
            'exclusions': []
        },
    })

  def cl_info():
    return api.json.output([{
        'owner': {
            # chromium-autoroller
            '_account_id': 1302611
        },
        'branch': 'master',
        'revisions': {
            'abcd1234': {
                '_number': '1',
                'commit': {
                    'message': 'Change commit message',
                },
            },
        },
    }])

  deps_changes = '''
13>src/third_party/fake_lib/fake_file.h
13>src/third_party/fake_lib/fake_file.cpp
14>third_party/fake_lib2/fake_file.cpp
'''

  def common_props():
    return sum([
        api.chromium.try_build(
            builder_group='tryserver.chromium.test',
            builder='retry-shards',
        ),
        api.chromium_tests.builders(
            bot_db.BotDatabase.create({
                'chromium.test': {
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
            })),
        api.chromium_tests.trybots(
            try_spec.TryDatabase.create({
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
                            analyze_deps_autorolls=True,
                        ),
                }
            })),
        api.properties(
            swarm_hashes={'base_unittests': '[dummy hash for base_unittests]'
                         },),
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
        api.override_step_data('read filter exclusion spec',
                               deps_exclusion_spec()),
        api.override_step_data('gerrit fetch current CL info', cl_info()),
        api.override_step_data('git diff to analyze patch',
                               api.raw_io.stream_output('DEPS')),
    ], api.empty_test_data())

  yield api.test(
      'analyze deps checker with dependency',
      common_props(),
      api.override_step_data(
          'Analyze DEPS autorolls.gclient recursively git diff all DEPS',
          api.raw_io.stream_output(deps_changes)),
      api.override_step_data(
          'analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['base_unittests'],
              'test_targets': ['base_unittests'],
          })),
      api.post_process(post_process.StepSuccess, 'base_unittests (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'analyze deps checker no dependency',
      common_props(),
      api.override_step_data(
          'Analyze DEPS autorolls.gclient recursively git diff all DEPS',
          api.raw_io.stream_output(deps_changes)),
      api.override_step_data(
          'analyze',
          api.json.output({
              'status': 'No dependency',
              'compile_targets': [],
              'test_targets': [],
          })),
      api.post_process(post_process.DoesNotRun, 'base_unittests (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'analyze deps checker empty affected',
      common_props(),
      api.override_step_data(
          'Analyze DEPS autorolls.gclient recursively git diff all DEPS',
          api.raw_io.stream_output('')),
      api.post_process(post_process.StepSuccess, 'Analyze DEPS autorolls.Skip'),
      api.post_process(post_process.StepSuccess, 'base_unittests (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'analyze deps infra fail',
      common_props(),
      api.override_step_data(
          'Analyze DEPS autorolls.gclient recursively git diff all DEPS',
          retcode=1,
      ),
      api.post_process(post_process.StepSuccess,
                       'Analyze DEPS autorolls.error'),
      api.post_process(post_process.StepSuccess, 'base_unittests (with patch)'),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from RECIPE_MODULES.build.chromium_tests import (bot_db, bot_spec, try_spec,
                                                 steps)

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'test_utils',
]


def RunSteps(api):
  assert api.tryserver.is_tryserver
  unrecoverable_test_suites = api.properties.get('unrecoverable_test_suites',
                                                 [])
  raw_result, task, build_config = api.chromium_tests._calculate_tests_to_run(
      builders=[],
      mirrored_bots=[],
      tests_to_run=[],
      root_solution_revision=None)
  api.chromium_tests.analyze_deps_autorolls(task.bot, build_config,
                                            unrecoverable_test_suites)
  return raw_result


def GenTests(api):
  deps_changes = '''
13>src/third_party/fake_lib/fake_file
13>src/third_party/fake_lib/fake_file_2
14>third_party/fake_lib2/fake_file_
'''
  cl_info = api.json.output([{
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

  analyze_result = api.json.output({
      'status': 'Found dependency',
      'compile_targets': ['test_suite'],
      'test_targets': ['test_suite'],
  })

  yield api.test(
      'pass',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          unrecoverable_test_suites=[steps.SwarmingGTestTest('test_suite')]),
      api.override_step_data('gerrit fetch current CL info', cl_info),
      api.override_step_data('git diff to analyze patch (2)',
                             api.raw_io.stream_output('DEPS')),
      api.override_step_data('gclient recursively git diff all DEPS',
                             api.raw_io.stream_output(deps_changes)),
      api.override_step_data('analyze (2)', analyze_result),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.StepSuccess, 'Analyze DEPS correct'),
  )

  yield api.test(
      'miss some suites',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          unrecoverable_test_suites=[steps.SwarmingGTestTest('test_suite')]),
      api.override_step_data('gerrit fetch current CL info', cl_info),
      api.override_step_data('git diff to analyze patch (2)',
                             api.raw_io.stream_output('DEPS')),
      api.override_step_data('gclient recursively git diff all DEPS',
                             api.raw_io.stream_output(deps_changes)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.StepSuccess, 'Analyze DEPS miss'),
  )

  yield api.test(
      'no changes detected',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.properties(
          unrecoverable_test_suites=[steps.SwarmingGTestTest('test_suite')]),
      api.override_step_data('gerrit fetch current CL info', cl_info),
      api.override_step_data('git diff to analyze patch (2)',
                             api.raw_io.stream_output('DEPS')),
      api.override_step_data('gclient recursively git diff all DEPS',
                             api.raw_io.stream_output('')),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.StepSuccess, 'Analyze DEPS skip'),
  )

# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from RECIPE_MODULES.build.chromium_tests import try_spec

DEPS = [
    'chromium',
    'chromium_tests',
    'depot_tools/tryserver',
    'recipe_engine/json',
    'recipe_engine/legacy_annotation',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  assert api.tryserver.is_tryserver
  raw_result = api.chromium_tests.trybot_steps()
  return raw_result


def GenTests(api):
  deps_exclusion_spec = lambda: api.json.output({
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

  # Apparently something modifies this output, so we create a new one each time
  cl_info = lambda: api.json.output([{
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

  yield api.test(
      'analyze deps checker pass',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.override_step_data('read filter exclusion spec',
                             deps_exclusion_spec()),
      api.override_step_data('gerrit fetch current CL info', cl_info()),
      api.override_step_data('git diff to analyze patch',
                             api.raw_io.stream_output('DEPS')),
      api.override_step_data(
          'Analyze DEPS autorolls.gclient recursively git diff all DEPS',
          api.raw_io.stream_output(deps_changes)),
      api.override_step_data(
          'Analyze DEPS autorolls.analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['base_unittests'],
              'test_targets': ['base_unittests'],
          })),
      api.override_step_data('base_unittests (with patch)',
                             api.legacy_annotation.failure_step),
      api.post_process(
          post_process.StepSuccess,
          'Analyze DEPS autorolls correctness check.Analyze DEPS correct'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'analyze deps checker empty affected',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.override_step_data('read filter exclusion spec',
                             deps_exclusion_spec()),
      api.override_step_data('gerrit fetch current CL info', cl_info()),
      api.override_step_data('git diff to analyze patch',
                             api.raw_io.stream_output('DEPS')),
      api.override_step_data(
          'Analyze DEPS autorolls.gclient recursively git diff all DEPS',
          api.raw_io.stream_output('')),
      api.override_step_data('base_unittests (with patch)',
                             api.legacy_annotation.failure_step),
      api.post_process(post_process.StepSuccess, 'Analyze DEPS autorolls.Skip'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'analyze deps checker empty analyze',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.override_step_data('read filter exclusion spec',
                             deps_exclusion_spec()),
      api.override_step_data('gerrit fetch current CL info', cl_info()),
      api.override_step_data('git diff to analyze patch',
                             api.raw_io.stream_output('DEPS')),
      api.override_step_data(
          'Analyze DEPS autorolls.gclient recursively git diff all DEPS',
          api.raw_io.stream_output(deps_changes)),
      api.override_step_data(
          'Analyze DEPS autorolls.analyze',
          api.json.output({
              'status': 'No dependency',
              'compile_targets': [],
              'test_targets': [],
          })),
      api.override_step_data('base_unittests (with patch)',
                             api.legacy_annotation.failure_step),
      api.post_process(
          post_process.StepSuccess,
          'Analyze DEPS autorolls correctness check.Analyze DEPS miss'),
      api.post_process(post_process.DropExpectation),
  )

  # make it run some suite other than the one that fails
  yield api.test(
      'analyze deps checker fail',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.override_step_data('read filter exclusion spec',
                             deps_exclusion_spec()),
      api.override_step_data('gerrit fetch current CL info', cl_info()),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.override_step_data('git diff to analyze patch',
                             api.raw_io.stream_output('DEPS')),
      api.override_step_data(
          'Analyze DEPS autorolls.gclient recursively git diff all DEPS',
          api.raw_io.stream_output(deps_changes)),
      api.override_step_data(
          'Analyze DEPS autorolls.analyze',
          api.json.output({
              'status': 'Found dependency',
              'compile_targets': ['not_base_unittests'],
              'test_targets': ['not_base_unittests'],
          })),
      api.override_step_data('base_unittests (with patch)',
                             api.legacy_annotation.failure_step),
      api.post_process(
          post_process.StepSuccess,
          'Analyze DEPS autorolls correctness check.Analyze DEPS miss'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'analyze deps checker infra fail',
      api.chromium.try_build(
          builder_group='tryserver.chromium.linux', builder='linux-rel'),
      api.override_step_data('read filter exclusion spec',
                             deps_exclusion_spec()),
      api.override_step_data('gerrit fetch current CL info', cl_info()),
      api.chromium_tests.read_source_side_spec('chromium.linux', {
          'Linux Tests': {
              'gtest_tests': ['base_unittests'],
          },
      }),
      api.override_step_data('git diff to analyze patch',
                             api.raw_io.stream_output('DEPS')),
      api.override_step_data(
          'Analyze DEPS autorolls.gclient recursively git diff all DEPS',
          retcode=1,
      ),
      api.post_process(post_process.StepSuccess,
                       'Analyze DEPS autorolls.error'),
      api.post_process(post_process.DropExpectation),
  )

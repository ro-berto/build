# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'code_coverage',
    'depot_tools/bot_update',
    'isolate',
    'recipe_engine/commit_position',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/step',
    'test_results',
    'test_utils',
]

from recipe_engine import post_process


def RunSteps(api):
  api.chromium.set_config(
    'chromium',
    TARGET_PLATFORM=api.properties.get('target_platform', 'linux'))

  # Fake path, as the real one depends on having done a chromium checkout.
  api.code_coverage._merge_scripts_location = api.path['start_dir']

  test = api.chromium_tests.steps.SwarmingIsolatedScriptTest(
      'base_unittests'
  )

  test_options = api.chromium_tests.steps.TestOptions()
  test.test_options = test_options

  test.pre_run(api, '')
  test.run(api, '')


def GenTests(api):
  def verify_log_fields(check, step_odict, expected_logs):
    step = step_odict['base_unittests']
    for log_title, expected_lines in expected_logs.iteritems():
      check(log_title in step.logs)
      for line in expected_lines:
        check(line in step.logs[log_title])

  def verify_link_fields(check, step_odict, expected_fields):
    step = step_odict['base_unittests']
    for link_title, url in expected_fields.iteritems():
      check(link_title in step.links)
      check(url == step.links[link_title])

  def verify_links_not_present(check ,step_odict, missing_links):
    step = step_odict['base_unittests']
    for missing_link_snippet in missing_links:
      for link_title in step.links:
        check(missing_link_snippet not in link_title)

  basic_artifacts = {
    'test1': {
      'Test1': {
        'somelink': ['https://somesite.com'],
      },
    },
  }
  basic_expectations = {
    'somelink for test1.Test1': 'https://somesite.com',
  }

  yield (
    api.test('basic') +
    api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
    api.override_step_data(
        'base_unittests',
        api.chromium_swarming.canned_summary_output(
            api.test_utils.canned_isolated_script_output(passing=True,
                use_json_test_format=True, artifacts=basic_artifacts),
            failure=False)) +
    api.post_process(verify_link_fields, basic_expectations) +
    api.post_process(post_process.DropExpectation)
  )

  bulk_log_title = ('Too many artifacts produced to link individually, click '
                    'for links')
  bulk_artifacts = {}
  bulk_expectations = {
    bulk_log_title: [],
  }
  for i in xrange(10):
    bulk_artifacts.setdefault('test1', {}).setdefault(
        'Test1', {})['%d' % i] = ['https://somesite.com']
    bulk_expectations[bulk_log_title].append(
        '%d for test1.Test1: https://somesite.com' % i)

  yield (
    api.test('bulk_log') +
    api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
    api.override_step_data(
        'base_unittests',
        api.chromium_swarming.canned_summary_output(
            api.test_utils.canned_isolated_script_output(passing=True,
                use_json_test_format=True, artifacts=bulk_artifacts),
            failure=False)) +
    api.post_process(verify_log_fields, bulk_expectations) +
    api.post_process(post_process.DropExpectation)
  )

  filepath_artifacts = {
    'test1': {
      'Test1': {
        'somelink': ['https://somesite.com', 'some/file/path'],
        'anotherlink': ['another/file/path'],
      }
    }
  }
  filepath_expectations = basic_expectations
  filepath_missing_links = ['some/file/path', 'another/file/path']

  yield (
    api.test('filepath') +
    api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
    api.override_step_data(
        'base_unittests',
        api.chromium_swarming.canned_summary_output(
            api.test_utils.canned_isolated_script_output(passing=True,
                use_json_test_format=True, artifacts=filepath_artifacts),
            failure=False)) +
    api.post_process(verify_link_fields, filepath_expectations) +
    api.post_process(verify_links_not_present, filepath_missing_links) +
    api.post_process(post_process.DropExpectation)
  )

  http_artifacts = {
    'test1': {
      'Test1': {
        'somelink': ['http://badsite.com'],
        'anotherlink': ['https://somesite.com'],
      },
    },
  }
  http_expectations = {
    'anotherlink for test1.Test1': 'https://somesite.com',
  }
  http_missing_links = ['badsite']

  yield (
    api.test('http') +
    api.properties(
          mastername='test_mastername',
          buildername='test_buildername',
          buildnumber=123,
          swarm_hashes={
            'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
          }) +
    api.override_step_data(
        'base_unittests',
        api.chromium_swarming.canned_summary_output(
            api.test_utils.canned_isolated_script_output(passing=True,
                use_json_test_format=True, artifacts=http_artifacts),
            failure=False)) +
    api.post_process(verify_link_fields, http_expectations) +
    api.post_process(verify_links_not_present, http_missing_links) +
    api.post_process(post_process.DropExpectation)
  )

  yield (
    api.test('corrupt_tests') +
    api.properties(
            mastername='test_mastername',
            buildername='test_buildername',
            buildnumber=123,
            swarm_hashes={
              'base_unittests': 'ffffffffffffffffffffffffffffffffffffffff',
            }) +
      api.override_step_data(
          'base_unittests',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(passing=True,
                  use_json_test_format=True, corrupt=True),
              failure=False)) +
      api.post_process(post_process.DropExpectation)
  )

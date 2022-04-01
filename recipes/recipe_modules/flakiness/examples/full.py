# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import base64

from google.protobuf import duration_pb2
from recipe_engine import post_process
from RECIPE_MODULES.build.chromium_tests import steps
from RECIPE_MODULES.build import chromium_tests_builder_config as ctbc

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import common as resultdb_common
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import resultdb as resultdb_pb2

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'filter',
    'flakiness',
    'py3_migration',
    'test_utils',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'recipe_engine/step',
]


def RunSteps(api):
  api.assertions.assertEqual(api.flakiness.gs_bucket, 'flake_endorser')
  api.assertions.assertEqual(
      api.flakiness.gs_source_template(experimental=True).format(
          'project', 'bucket', 'builder', 'latest'),
      'experimental/project/bucket/builder/latest/')

  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  with api.chromium.chromium_layout():
    api.chromium_tests.report_builders(builder_config)
    _, task = api.chromium_tests.build_affected_targets(builder_id,
                                                        builder_config)

    if api.properties.get('assert_tests'):
      assert task.test_suites

    api.step.empty('mark: before_tests')

    _, unrecoverable_test_suites = api.chromium_tests._run_tests_with_retries(
        builder_id, task, api.chromium_tests.deapply_patch)

    api.chromium_swarming.report_stats()
    api.chromium_tests.handle_invalid_test_suites(unrecoverable_test_suites)

    new_tests = api.flakiness.find_tests_for_flakiness(
        test_objects=task.test_suites)
    if new_tests:
      return api.chromium_tests.run_tests_for_flakiness(builder_config,
                                                        new_tests)


def GenTests(api):
  builder = builder_pb2.BuilderID(
      builder='fake-try-builder', project='chromium', bucket='try')

  def _generate_variant(**kwargs):
    variant = resultdb_common.Variant()
    variant_def = getattr(variant, 'def')
    for k, v in kwargs.items():
      variant_def[str(k)] = str(v)
    return variant

  all_mismatched = _generate_variant(
      os='Ubuntu-14.04',
      test_suite='ios_chrome_bookmarks_eg2tests_module_iPhone 11 14.4')
  correct_variant = _generate_variant(
      os='Mac-11',
      test_suite='ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4')
  correct_variant_another_suite = _generate_variant(
      os='Mac-11', test_suite='ios_chrome_web_eg2tests_module_iPad Air 2 14.4')

  # Populate build_database with two builds and two invocations.
  # Generating 10 builds into the build_database, each with an invocation
  # containing 2 failed test results. Total of 20 test results.
  test_id = (
      'ninja://ios/chrome/test/earl_grey2:ios_chrome_bookmarks_eg2tests_module/'
      'TestSuite.test_a')

  same_suite_another_test_id = (
      'ninja://ios/chrome/test/earl_grey2:ios_chrome_bookmarks_eg2tests_module/'
      'TestSuite.test_b')

  another_suite_another_test_id = (
      'ninja://ios/chrome/test/earl_grey2:ios_chrome_web_eg2tests_module/'
      'TestSuite.test_c')

  def _generate_build(builder, invocation, build_input=None):
    return build_pb2.Build(
        builder=builder,
        infra=build_pb2.BuildInfra(
            resultdb=build_pb2.BuildInfra.ResultDB(invocation=invocation)),
        input=build_input)

  def _generate_test_result(test_id,
                            test_variant,
                            status=None,
                            tags=None,
                            test_duration=10):
    status = status or test_result_pb2.PASS
    vd = getattr(test_variant, 'def')
    vh_in = '\n'.join(
        '{}:{}'.format(k, v)
        for k, v in api.py3_migration.consistent_ordering(vd.items()))
    vh = base64.b64encode(vh_in.encode('utf-8')).decode('utf-8')
    duration = duration_pb2.Duration()
    duration.FromMilliseconds(test_duration)
    tr = test_result_pb2.TestResult(
        test_id=test_id,
        variant=test_variant,
        variant_hash=vh,
        expected=status == test_result_pb2.PASS,
        status=status,
        duration=duration,
    )
    if tags:
      all_tags = getattr(tr, 'tags')
      all_tags.append(tags)
    return tr

  build_database = []
  current_patchset_bookmark_suite_invocations = {}
  current_patchset_web_suite_invocations = {}
  current_patchset_web_suite_invocations_long_test = {}
  for i in range(3):
    inv = "invocations/{}".format(i + 1)
    build = _generate_build(builder, inv)
    build_database.append(build)

    if i == 0:
      test_results_bookmark_suite = [
          _generate_test_result(test_id, correct_variant),
          _generate_test_result(same_suite_another_test_id, correct_variant),
      ]
    else:
      test_results_bookmark_suite = [
          _generate_test_result(test_id, correct_variant),
      ]
    current_patchset_bookmark_suite_invocations[inv] = api.resultdb.Invocation(
        test_results=test_results_bookmark_suite)

  test_results_web_suite = [
      _generate_test_result(
          another_suite_another_test_id,
          correct_variant_another_suite,
          test_duration=0),
  ]
  current_patchset_web_suite_invocations['invocations/web'] = (
      api.resultdb.Invocation(test_results=test_results_web_suite))

  test_results_web_suite_long_test = [
      _generate_test_result(
          another_suite_another_test_id,
          correct_variant_another_suite,
          test_duration=96000),
  ]

  current_patchset_web_suite_invocations_long_test['invocations/web'] = (
      api.resultdb.Invocation(test_results=test_results_web_suite_long_test))

  # This is what's been most recently run as part of verification, and will be
  # removed as it's a false positive.
  res = resultdb_pb2.GetTestResultHistoryResponse(entries=[
      resultdb_pb2.GetTestResultHistoryResponse.Entry(
          result=_generate_test_result(test_id, all_mismatched)),
  ])

  excluded_build = _generate_build(
      builder,
      'invocations/3',
      build_input=build_pb2.Build.Input(gerrit_changes=[
          common_pb2.GerritChange(
              host='chromium-review.googlesource.com',
              project='chromium/src',
              change=10,
              patchset=3,
          )
      ]))

  builder_db = ctbc.BuilderDatabase.create({
      'fake-group': {
          'fake-builder':
              ctbc.BuilderSpec.create(
                  chromium_config='chromium',
                  gclient_config='chromium',
              ),
          'fake-android-builder':
              ctbc.BuilderSpec.create(
                  android_config='main_builder_mb',
                  chromium_config='android',
                  gclient_config='chromium',
                  gclient_apply_config=[
                      'android',
                  ],
                  chromium_config_kwargs={
                      'BUILD_CONFIG': 'Release',
                      'TARGET_BITS': 32,
                      'TARGET_PLATFORM': 'android',
                  }),
      },
  })

  yield api.test(
      'basic_ios',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                      ),
              },
          })),
      api.properties(assert_tests=True),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'isolated_scripts': [
                      {
                          "isolate_name":
                              "ios_chrome_bookmarks_eg2tests_module",
                          "name": ("ios_chrome_bookmarks_eg2tests_module_iPad "
                                   "Air 2 14.4"),
                          "swarming": {
                              "can_use_on_swarming_builders": True,
                              "dimension_sets": [{
                                  "os": "Mac-11"
                              }],
                              "shards": 2,
                          },
                          "test_id_prefix":
                              ("ninja://ios/chrome/test/earl_grey2:"
                               "ios_chrome_bookmarks_eg2tests_module/")
                      },
                      {
                          "isolate_name":
                              "ios_chrome_web_eg2tests_module",
                          "name": ("ios_chrome_web_eg2tests_module_iPad "
                                   "Air 2 14.4"),
                          "swarming": {
                              "can_use_on_swarming_builders": True,
                              "dimension_sets": [{
                                  "os": "Mac-11"
                              }],
                              "shards": 1,
                          },
                          "test_id_prefix":
                              ("ninja://ios/chrome/test/earl_grey2:"
                               "ios_chrome_web_eg2tests_module/")
                      },
                  ],
              },
          }),
      api.filter.suppress_analyze(),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.override_step_data(
          ('ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(with patch) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
              ),
              failure=False)),
      api.override_step_data(('ios_chrome_web_eg2tests_module_iPad Air 2 14.4 '
                              '(with patch) on Mac-11'),
                             api.chromium_swarming.canned_summary_output(
                                 api.test_utils.canned_isolated_script_output(
                                     passing=True,
                                     is_win=False,
                                     swarming=True,
                                 ),
                                 failure=False)),
      api.resultdb.query(
          current_patchset_bookmark_suite_invocations,
          ('collect tasks (with patch).'
           'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 results'),
      ),
      api.resultdb.query(
          current_patchset_web_suite_invocations,
          ('collect tasks (with patch).'
           'ios_chrome_web_eg2tests_module_iPad Air 2 14.4 results'),
      ),
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      # This is the related build that'll be excluded, which includes itself.
      api.buildbucket.simulated_search_results(
          builds=[excluded_build],
          step_name=(
              'searching_for_new_tests.'
              'fetching associated builds with current gerrit patchset')),
      # This is what's been recently run, and that isn't in the exclusion list
      # and so should be removed (false positive).
      api.resultdb.get_test_result_history(
          res,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.override_step_data(
          ('test new tests for flakiness.'
           'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(check flakiness shard #0) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
              ),
              failure=False)),
      api.override_step_data(('test new tests for flakiness.'
                              'ios_chrome_web_eg2tests_module_iPad Air 2 14.4 '
                              '(check flakiness shard #0) on Mac-11'),
                             api.chromium_swarming.canned_summary_output(
                                 api.test_utils.canned_isolated_script_output(
                                     passing=True,
                                     is_win=False,
                                     swarming=True,
                                 ),
                                 failure=False)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  tags = resultdb_common.StringPair(
      key='test_name',
      value=('org.chromium.chrome.browser.safety_check.'
             'SafetyCheckMediatorTest#testUpdatesCheckUpdated[0]'))
  linux_variant = _generate_variant(
      os='Ubuntu-16', test_suite='chrome_junit_tests')
  junit_invocations = {
      'invocations/build:8945511751514863184':
          api.resultdb.Invocation(test_results=[
              _generate_test_result(
                  test_id=(
                      'ninja://chrome/android:chrome_junit_tests/'
                      'org.chromium.chrome.browser.safety_check.'
                      'SafetyCheckMediatorTest#testUpdatesCheckUpdated[0]'),
                  test_variant=linux_variant,
                  tags=tags),
          ])
  }

  yield api.test(
      'basic_junit_tests',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-android-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-android-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-android-builder',
                      ),
              },
          })),
      api.properties(assert_tests=True),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-android-builder': {
                  'junit_tests': [{
                      'isolate_profile_data':
                          True,
                      'name':
                          'chrome_junit_tests',
                      'resultdb': {
                          'enable': True,
                          'has_native_resultdb_integration': True
                      },
                      'swarming': {},
                      'test':
                          'chrome_junit_tests',
                      'test_id_prefix':
                          'ninja://chrome/android:chrome_junit_tests/'
                  }],
              },
          }),
      api.filter.suppress_analyze(),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.resultdb.query(
          junit_invocations,
          ('chrome_junit_tests results'),
      ),
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.resultdb.get_test_result_history(
          resultdb_pb2.GetTestResultHistoryResponse(entries=[]),
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.post_process(
          post_process.StepCommandContains,
          ('test new tests for flakiness.chrome_junit_tests '
           '(check flakiness shard #0)'),
          ('--gtest_filter=org.chromium.chrome.browser.safety_check.'
           'SafetyCheckMediatorTest#testUpdatesCheckUpdated\\[0\\]')),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  non_param_tags = resultdb_common.StringPair(
      key='test_name',
      value=('org.chromium.chrome.browser.safety_check.'
             'SafetyCheckMediatorTest#testUpdatesCheckUpdated'))
  junit_nonparameterized_invocation = {
      'invocations/build:8945511751514863184':
          api.resultdb.Invocation(test_results=[
              _generate_test_result(
                  test_id=('ninja://chrome/android:chrome_junit_tests/'
                           'org.chromium.chrome.browser.safety_check.'
                           'SafetyCheckMediatorTest#testUpdatesCheckUpdated'),
                  test_variant=linux_variant,
                  tags=non_param_tags),
          ])
  }

  yield api.test(
      'basic_junit_non_parameterized_tests',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-android-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-android-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-android-builder',
                      ),
              },
          })),
      api.properties(assert_tests=True),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-android-builder': {
                  'junit_tests': [{
                      'isolate_profile_data':
                          True,
                      'name':
                          'chrome_junit_tests',
                      'resultdb': {
                          'enable': True,
                          'has_native_resultdb_integration': True
                      },
                      'swarming': {},
                      'test':
                          'chrome_junit_tests',
                      'test_id_prefix':
                          'ninja://chrome/android:chrome_junit_tests/'
                  }],
              },
          }),
      api.filter.suppress_analyze(),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.resultdb.query(
          junit_nonparameterized_invocation,
          ('chrome_junit_tests results'),
      ),
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.resultdb.get_test_result_history(
          resultdb_pb2.GetTestResultHistoryResponse(entries=[]),
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.post_process(
          post_process.StepCommandContains,
          ('test new tests for flakiness.chrome_junit_tests '
           '(check flakiness shard #0)'),
          ('--gtest_filter=org.chromium.chrome.browser.safety_check.'
           'SafetyCheckMediatorTest#testUpdatesCheckUpdated')),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  tags = resultdb_common.StringPair(
      key='test_name', value='check_network_annotations')
  linux_variant = _generate_variant(
      os='Ubuntu-16', test_suite='check_network_annotations')
  script_invocation = {
      'invocations/build:8945511751514863184':
          api.resultdb.Invocation(test_results=[
              _generate_test_result(
                  test_id='check_network_annotations',
                  test_variant=linux_variant)
          ])
  }

  yield api.test(
      'basic_scripts_tests',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-android-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-android-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-android-builder',
                      ),
              },
          })),
      api.properties(assert_tests=True),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-android-builder': {
                  'scripts': [{
                      'isolate_profile_data': True,
                      'name': 'check_network_annotations',
                      'resultdb': {
                          'enable': True,
                          'has_native_resultdb_integration': True
                      },
                      'script': 'check_network_annotations.py',
                      'swarming': {}
                  }],
              },
          }),
      api.filter.suppress_analyze(),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.resultdb.query(
          script_invocation,
          ('check_network_annotations results'),
      ),
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      api.resultdb.get_test_result_history(
          resultdb_pb2.GetTestResultHistoryResponse(entries=[]),
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic_ios_sharded',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                      ),
              },
          })),
      api.properties(assert_tests=True),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'isolated_scripts': [{
                      "isolate_name":
                          "ios_chrome_web_eg2tests_module",
                      "name": ("ios_chrome_web_eg2tests_module_iPad "
                               "Air 2 14.4"),
                      "swarming": {
                          "can_use_on_swarming_builders": True,
                          "dimension_sets": [{
                              "os": "Mac-11"
                          }],
                          "shards": 1,
                      },
                      "test_id_prefix": ("ninja://ios/chrome/test/earl_grey2:"
                                         "ios_chrome_web_eg2tests_module/")
                  },],
              },
          }),
      api.filter.suppress_analyze(),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.override_step_data(('ios_chrome_web_eg2tests_module_iPad Air 2 14.4 '
                              '(with patch) on Mac-11'),
                             api.chromium_swarming.canned_summary_output(
                                 api.test_utils.canned_isolated_script_output(
                                     passing=True,
                                     is_win=False,
                                     swarming=True,
                                 ),
                                 failure=False)),
      api.resultdb.query(
          current_patchset_web_suite_invocations_long_test,
          ('collect tasks (with patch).'
           'ios_chrome_web_eg2tests_module_iPad Air 2 14.4 results'),
      ),
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      # This is the related build that'll be excluded, which includes itself.
      api.buildbucket.simulated_search_results(
          builds=[excluded_build],
          step_name=(
              'searching_for_new_tests.'
              'fetching associated builds with current gerrit patchset')),
      # This is what's been recently run, and that isn't in the exclusion list
      # and so should be removed (false positive).
      api.resultdb.get_test_result_history(
          res,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.override_step_data(('test new tests for flakiness.'
                              'ios_chrome_web_eg2tests_module_iPad Air 2 14.4 '
                              '(check flakiness shard #0) on Mac-11'),
                             api.chromium_swarming.canned_summary_output(
                                 api.test_utils.canned_isolated_script_output(
                                     passing=True,
                                     is_win=False,
                                     swarming=True,
                                 ),
                                 failure=False)),
      api.override_step_data(('test new tests for flakiness.'
                              'ios_chrome_web_eg2tests_module_iPad Air 2 14.4 '
                              '(check flakiness shard #1) on Mac-11'),
                             api.chromium_swarming.canned_summary_output(
                                 api.test_utils.canned_isolated_script_output(
                                     passing=True,
                                     is_win=False,
                                     swarming=True,
                                 ),
                                 failure=False)),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  flaky_results = {
      'invocations/100':
          api.resultdb.Invocation(test_results=[
              _generate_test_result(test_id, correct_variant),
              _generate_test_result(
                  test_id, correct_variant, status=test_result_pb2.FAIL)
          ])
  }

  yield api.test(
      'basic_ios_test_failure',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                      ),
              },
          })),
      api.properties(assert_tests=True),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'isolated_scripts': [{
                      "isolate_name":
                          "ios_chrome_bookmarks_eg2tests_module",
                      "name": ("ios_chrome_bookmarks_eg2tests_module_iPad "
                               "Air 2 14.4"),
                      "swarming": {
                          "can_use_on_swarming_builders": True,
                          "dimension_sets": [{
                              "os": "Mac-11"
                          }],
                      },
                      "test_id_prefix":
                          ("ninja://ios/chrome/test/earl_grey2:"
                           "ios_chrome_bookmarks_eg2tests_module/")
                  },],
              },
          }),
      api.filter.suppress_analyze(),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.override_step_data(
          ('ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(with patch) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
              ),
              failure=False)),
      api.resultdb.query(
          current_patchset_bookmark_suite_invocations,
          ('collect tasks (with patch).'
           'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 results'),
      ),
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      # This is the related build that'll be excluded, which includes itself.
      api.buildbucket.simulated_search_results(
          builds=[excluded_build],
          step_name=(
              'searching_for_new_tests.'
              'fetching associated builds with current gerrit patchset')),
      api.resultdb.get_test_result_history(
          res,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.override_step_data(
          ('test new tests for flakiness.'
           'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(check flakiness shard #0) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
              ),
              failure=True)),
      api.resultdb.query(
          inv_bundle=flaky_results,
          step_name=(
              'test new tests for flakiness.'
              'collect tasks (check flakiness shard #0).'
              'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 results')),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'basic_ios_test_failure_experimental_suite',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                      ),
              },
          })),
      api.properties(assert_tests=True),
      api.chromium_tests.read_source_side_spec(
          'fake-group', {
              'fake-builder': {
                  'isolated_scripts': [{
                      "isolate_name":
                          "ios_chrome_bookmarks_eg2tests_module",
                      "name": ("ios_chrome_bookmarks_eg2tests_module_iPad "
                               "Air 2 14.4"),
                      "swarming": {
                          "can_use_on_swarming_builders": True,
                          "dimension_sets": [{
                              "os": "Mac-11"
                          }],
                      },
                      "experiment_percentage":
                          100,
                      "test_id_prefix":
                          ("ninja://ios/chrome/test/earl_grey2:"
                           "ios_chrome_bookmarks_eg2tests_module/")
                  },],
              },
          }),
      api.filter.suppress_analyze(),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.override_step_data(
          ('ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(with patch, experimental) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
              ),
              failure=False)),
      api.resultdb.query(
          current_patchset_bookmark_suite_invocations,
          'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 results',
      ),
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      # This is the related build that'll be excluded, which includes itself.
      api.buildbucket.simulated_search_results(
          builds=[excluded_build],
          step_name=(
              'searching_for_new_tests.'
              'fetching associated builds with current gerrit patchset')),
      api.resultdb.get_test_result_history(
          res,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.override_step_data(
          ('test new tests for flakiness.'
           'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(check flakiness shard #0, experimental) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  swarming=True,
              ),
              failure=True)),
      api.resultdb.query(
          inv_bundle=flaky_results,
          step_name=(
              'test new tests for flakiness.'
              'ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 results')),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip identifying at DEPS file change',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                      ),
              },
          })),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.filter.suppress_analyze(),
      api.step_data('git diff to analyze patch (2)',
                    api.raw_io.stream_output('chrome/file1.cc\nsrc/DEPS')),
      api.post_check(post_process.MustRun,
                     'no test files were detected with this change.'),
      api.post_check(post_process.DoesNotRun, 'searching_for_new_tests'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip identifying when no test file change',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                      ),
              },
          })),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.filter.suppress_analyze(),
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/file1.cc\ncomponents/file2.cc')),
      api.post_check(post_process.MustRun,
                     'no test files were detected with this change.'),
      api.post_check(post_process.DoesNotRun, 'searching_for_new_tests'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip footer',
      api.chromium_tests_builder_config.try_build(
          builder_group='fake-try-group',
          builder='fake-try-builder',
          builder_db=builder_db,
          try_db=ctbc.TryDatabase.create({
              'fake-try-group': {
                  'fake-try-builder':
                      ctbc.TrySpec.create_for_single_mirror(
                          builder_group='fake-group',
                          buildername='fake-builder',
                      ),
              },
          })),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.filter.suppress_analyze(),
      api.step_data('parse description',
                    api.json.output({'Validate-Test-Flakiness': ['Skip']})),
      api.post_check(
          post_process.MustRun, 'skipping flaky test check since commit footer '
          '\'Validate-Test-Flakiness: Skip\' was detected.'),
      api.post_check(post_process.DoesNotRun, 'searching_for_new_tests'),
      api.post_process(post_process.DropExpectation),
  )

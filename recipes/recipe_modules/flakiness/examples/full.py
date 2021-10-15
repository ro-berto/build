# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64

from recipe_engine import post_process
from RECIPE_MODULES.build.chromium_tests import steps
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import common as resultdb_common
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import resultdb as resultdb_pb2

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'filter',
    'flakiness',
    'depot_tools/gclient',
    'depot_tools/tryserver',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/resultdb',
    'test_utils',
]


def RunSteps(api):
  builder_id, builder_config = (
      api.chromium_tests_builder_config.lookup_builder())
  with api.chromium.chromium_layout():
    api.chromium_tests.report_builders(builder_config)
    _, task = api.chromium_tests.build_affected_targets(builder_id,
                                                        builder_config)

    if api.properties.get('assert_tests'):
      assert task.test_suites

    api.python.succeeding_step('mark: before_tests', '')

    _, unrecoverable_test_suites = api.chromium_tests._run_tests_with_retries(
        builder_id, task, api.chromium_tests.deapply_patch)

    api.chromium_swarming.report_stats()
    api.chromium_tests.handle_invalid_test_suites(unrecoverable_test_suites)

    api.flakiness.check_tests_for_flakiness(test_objects=task.test_suites)


def GenTests(api):
  builder = builder_pb2.BuilderID(
      builder='ios-simulator-full-configs', project='chromium', bucket='try')

  def _generate_variant(**kwargs):
    variant = resultdb_common.Variant()
    variant_def = getattr(variant, 'def')
    for k, v in kwargs.items():
      variant_def[str(k)] = str(v)
    return variant

  all_mismatched = _generate_variant(
      os='Ubuntu-14.04',
      test_suite='ios_chrome_bookmarks_eg2tests_module_iPhone 11 14.4')
  mismatched_test_suite = _generate_variant(
      os='Mac-11',
      test_suite='ios_chrome_bookmarks_eg2tests_module_iPhone 11 14.4')
  mismatched_os = _generate_variant(
      os='Ubuntu-14.04',
      test_suite='ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4')
  correct_variant = _generate_variant(
      os='Mac-11',
      test_suite='ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4')

  # Populate build_database with two builds and two invocations.
  # Generating 10 builds into the build_database, each with an invocation
  # containing 2 failed test results. Total of 20 test results.
  test_id = (
      'ninja://ios/chrome/test/earl_grey2:ios_chrome_bookmarks_eg2tests_module/'
      'TestSuite.test_a')

  def _generate_build(builder, invocation, build_input=None):
    return build_pb2.Build(
        builder=builder,
        infra=build_pb2.BuildInfra(
            resultdb=build_pb2.BuildInfra.ResultDB(invocation=invocation)),
        input=build_input)

  def _generate_test_result(test_id, test_variant):
    vd = getattr(test_variant, 'def')
    vh = str(
        base64.b64encode('\n'.join(
            '{}:{}'.format(k, v) for k, v in vd.items())))
    return test_result_pb2.TestResult(
        test_id=test_id,
        variant=test_variant,
        variant_hash=vh,
        expected=False,
        status=test_result_pb2.FAIL,
    )

  build_database, current_patchset_invocations = [], {}
  for i in range(2):
    inv = "invocations/{}".format(i + 1)
    build = _generate_build(builder, inv)
    build_database.append(build)

    if i == 0:
      test_results = [
          _generate_test_result(test_id, all_mismatched),
          _generate_test_result(test_id, mismatched_test_suite),
          _generate_test_result(test_id, mismatched_os),
          _generate_test_result(test_id, correct_variant),
      ]
    else:
      test_results = [
          _generate_test_result(test_id, all_mismatched),
      ]
    current_patchset_invocations[inv] = api.resultdb.Invocation(
        test_results=test_results)

  # This is what's been most recently run as part of verification, and will be
  # removed as it's a false positive.
  res = resultdb_pb2.GetTestResultHistoryResponse(entries=[
      resultdb_pb2.GetTestResultHistoryResponse.Entry(
          result=_generate_test_result(test_id, all_mismatched)),
  ])

  # This is for the current build
  current_build = _generate_build(
      builder,
      'invocations/4',
      build_input=build_pb2.Build.Input(gerrit_changes=[
          common_pb2.GerritChange(
              host='chromium-review.googlesource.com',
              project='chromium/src',
              change=10,
              patchset=3,
          )
      ]))

  data = api.chromium._common_test_data(
      bot_id='test_bot', default_builder_group='tryserver.chromium.mac')

  yield api.test(
      'basic_ios',
      data + api.buildbucket.build(current_build),
      api.properties(xcode_build_version='13a233', assert_tests=True),
      api.chromium_tests.read_source_side_spec(
          'chromium.mac', {
              'ios-simulator-full-configs': {
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
      # This overrides the file check to ensure that we have test files
      # in the given patch.
      api.step_data(
          'git diff to analyze patch (2)',
          api.raw_io.stream_output('chrome/test.cc\ncomponents/file2.cc')),
      # This is the related build that'll be excluded, which includes itself.
      api.buildbucket.simulated_search_results(
          builds=[current_build],
          step_name=(
              'searching_for_new_tests.'
              'fetching associated builds with current gerrit patchset')),
      # Search for all past invocations for builder
      api.buildbucket.simulated_search_results(
          builds=build_database,
          step_name='searching_for_new_tests.fetch previously run invocations'),
      api.resultdb.query(
          inv_bundle=current_patchset_invocations,
          step_name=('searching_for_new_tests.'
                     'fetch test variants for current patchset')),
      api.resultdb.query(
          inv_bundle={
              'invocations/2': current_patchset_invocations['invocations/2']
          },
          step_name=('searching_for_new_tests.'
                     'fetch test variants from previous invocations')),
      # This is what's been recently run, and that isn't in the exclusion list
      # and so should be removed (false positive).
      api.resultdb.get_test_result_history(
          res,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.override_step_data(
          ('ios_chrome_bookmarks_eg2tests_module_iPad Air 2 14.4 '
           '(check flakiness) on Mac-11'),
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_isolated_script_output(
                  passing=True,
                  is_win=False,
                  swarming=True,
              ),
              failure=False)),
  )

  yield api.test(
      'skip identifying when no test file change',
      api.chromium.try_build(
          builder_group='tryserver.chromium.mac',
          builder='ios-simulator-full-configs',
      ),
      api.properties(xcode_build_version='13a233'),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.filter.suppress_analyze(),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip footer',
      api.chromium.try_build(
          builder_group='tryserver.chromium.mac',
          builder='ios-simulator-full-configs',
      ),
      api.properties(xcode_build_version='13a233'),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.filter.suppress_analyze(),
      api.step_data('parse description',
                    api.json.output({'Validate-Test-Flakiness': ['Skip']})),
      api.post_process(post_process.DropExpectation),
  )

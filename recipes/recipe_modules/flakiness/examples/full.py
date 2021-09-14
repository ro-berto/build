# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import resultdb as resultdb_pb2

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'flakiness',
    'depot_tools/tryserver',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/resultdb',
]


def RunSteps(api):
  new_tests = {
      'test1_invocations/2hash',
      'test1_invocations/4hash',
      'test1_invocations/5hash',
      'test1_invocations/6hash',
      'test1_invocations/7hash',
      'test1_invocations/8hash',
      'test1_invocations/9hash',
      'test1_invocations/10hash',
      'test2_invocations/2hash',
      'test2_invocations/3hash',
      'test2_invocations/4hash',
      'test2_invocations/5hash',
      'test2_invocations/6hash',
      'test2_invocations/7hash',
      'test2_invocations/8hash',
      'test2_invocations/9hash',
      'test2_invocations/10hash',
  }
  found_tests = api.flakiness.check_tests_for_flakiness()
  if found_tests:
    found_tests = set([
        str('_'.join([test_id, variant_hash]))
        for test_id, variant_hash in found_tests
    ])
    api.assertions.assertEqual(new_tests, found_tests)
  else:
    api.assertions.assertFalse(found_tests)


def GenTests(api):
  build_database, inv_bundle = [], {}
  for i in range(10):
    inv = "invocations/{}".format(i + 1)
    build = build_pb2.Build(
        builder=builder_pb2.BuilderID(builder='Builder'),
        infra=build_pb2.BuildInfra(
            resultdb=build_pb2.BuildInfra.ResultDB(invocation=inv)),
    )
    build_database.append(build)
    test_results = [
        test_result_pb2.TestResult(
            test_id='test1',
            variant_hash='{}hash'.format(inv),
            expected=False,
            status=test_result_pb2.FAIL,
        ),
        test_result_pb2.TestResult(
            test_id='test2',
            variant_hash='{}hash'.format(inv),
            expected=False,
            status=test_result_pb2.FAIL,
        ),
    ]
    inv_bundle[inv] = api.resultdb.Invocation(test_results=test_results)

  basic_build = build_pb2.Build(
      builder=builder_pb2.BuilderID(
          builder='Builder', project='chromium', bucket='try'),
      infra=build_pb2.BuildInfra(
          resultdb=build_pb2.BuildInfra.ResultDB(invocation='invocations/100')),
      input=build_pb2.Build.Input(
          gerrit_changes=[
              common_pb2.GerritChange(
                  host='chromium-review.googlesource.com',
                  project='chromium/src',
                  change=10,
                  patchset=3,
              )
          ],))

  res = resultdb_pb2.GetTestResultHistoryResponse(entries=[
      resultdb_pb2.GetTestResultHistoryResponse.Entry(
          result=test_result_pb2.TestResult(
              test_id='test1',
              variant_hash='invocations/3hash',
              expected=False,
              status=test_result_pb2.FAIL,
          ))
  ])

  yield api.test(
      'basic',
      api.buildbucket.build(basic_build),
      api.flakiness(
          identify_new_tests=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.buildbucket.simulated_search_results(
          builds=[basic_build],
          step_name='searching_for_new_tests.fetching_builds_for_given_cl'),
      api.buildbucket.simulated_search_results(
          builds=build_database,
          step_name='searching_for_new_tests.get_historical_invocations'),
      api.resultdb.query(
          inv_bundle=inv_bundle,
          step_name='searching_for_new_tests.get_current_cl_test_variants'),
      api.resultdb.query(
          inv_bundle={'invocations/1': inv_bundle['invocations/1']},
          step_name='searching_for_new_tests.get_historical_test_variants'),
      api.resultdb.get_test_result_history(
          res, step_name='searching_for_new_tests.verify_new_tests'),
      api.post_process(post_process.StepCommandContains,
                       'searching_for_new_tests.verify_new_tests', [
                           'rdb',
                           'rpc',
                           'luci.resultdb.v1.ResultDB',
                           'GetTestResultHistory',
                       ]),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no identification',
      api.buildbucket.try_build(
          'chromium',
          'mac',
          git_repo='https://chromium.googlesource.com/chromium/src',
          change_number=91827,
          patch_set=1),
      api.flakiness(
          identify_new_tests=False,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'skip footer',
      api.buildbucket.try_build(
          'chromium',
          'mac',
          git_repo='https://chromium.googlesource.com/chromium/src',
          change_number=91827,
          patch_set=1),
      api.tryserver.gerrit_change_target_ref('refs/heads/experiment'),
      api.flakiness(
          identify_new_tests=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.step_data('parse description',
                    api.json.output({'Validate-Test-Flakiness': ['Skip']})),
      api.post_process(post_process.DropExpectation),
  )

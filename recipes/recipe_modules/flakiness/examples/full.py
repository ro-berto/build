# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2

DEPS = [
    'flakiness',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/resultdb',
]


def RunSteps(api):
  new_tests = {
      'test1_invocations/2hash',
      'test1_invocations/3hash',
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
  found_tests = api.flakiness.identify_new_tests()
  api.assertions.assertEqual(new_tests, found_tests)


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

    inv_bundle[inv] = api.resultdb.Invocation(test_results=[
        test_result_pb2.TestResult(
            test_id='test1', variant_hash='{}hash'.format(inv)),
        test_result_pb2.TestResult(
            test_id='test2', variant_hash='{}hash'.format(inv)),
    ])

  basic_build = build_pb2.Build(
      builder=builder_pb2.BuilderID(builder='Builder'),
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

  yield api.test(
      'basic',
      api.buildbucket.build(basic_build),
      api.flakiness(
          identify_new_tests=True, build_count=10, test_query_count=2),
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
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no identification',
      api.flakiness(
          identify_new_tests=False, build_count=10, test_query_count=2),
      api.expect_exception('AssertionError'),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 import common as rdb_common_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import test_result as test_result_pb2
from PB.go.chromium.org.luci.resultdb.proto.v1 \
    import resultdb as resultdb_pb2

from recipe_engine import recipe_api
from recipe_engine import recipe_test_api

PYTHON_VERSION_COMPATIBILITY = "PY2+3"

DEPS = [
    'flakiness',
    'depot_tools/tryserver',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/file',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/resultdb',
]


def RunSteps(api):
  new_tests = {
      'ninja://sample/test:some_test/TestSuite.Test2_2hash_False',
      'ninja://sample/test:some_test/TestSuite.Test3_3hash_False',
      'ninja://sample/test:some_test/TestSuite.Test4_4hash_False',
  }
  found_tests = api.flakiness.identify_new_tests()
  if found_tests:
    found_tests = set([
        str('_'.join([t.test_id, t.variant_hash,
                      str(t.is_experimental)])) for t in found_tests
    ])
    api.assertions.assertEqual(new_tests, found_tests)


def GenTests(api):
  build_database, inv_bundle = [], {}
  non_experimental_tags = [
      rdb_common_pb2.StringPair(
          key='step_name', value='some test (with patch)')
  ]
  for i in range(5):
    inv = "invocations/{}".format(i + 1)
    build = build_pb2.Build(
        builder=builder_pb2.BuilderID(builder='Builder'),
        infra=build_pb2.BuildInfra(
            resultdb=build_pb2.BuildInfra.ResultDB(invocation=inv)),
    )
    build_database.append(build)
    test_results = [
        test_result_pb2.TestResult(
            test_id='ninja://sample/test:some_test/TestSuite.Test' + str(i),
            variant_hash='{}hash'.format(i),
            expected=False,
            status=test_result_pb2.FAIL,
            tags=non_experimental_tags,
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
              test_id='ninja://sample/test:some_test/TestSuite.Test1',
              variant_hash='1hash',
              expected=False,
              status=test_result_pb2.FAIL,
          ))
  ])

  yield api.test(
      'basic',
      api.buildbucket.build(basic_build),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.buildbucket.simulated_search_results(
          builds=[basic_build],
          step_name=('searching_for_new_tests.fetching associated builds with '
                     'current gerrit patchset')),
      api.resultdb.query(
          inv_bundle=inv_bundle,
          step_name=('searching_for_new_tests.'
                     'fetch test variants for current patchset')),
      api.step_data(
          'searching_for_new_tests.process precomputed test history',
          api.file.read_json([{
              'test_id': 'ninja://sample/test:some_test/TestSuite.Test2',
              'variant_hash': '2hash',
              'is_experimental': True,
              'invocation': ['invocation/3']
          }, {
              'test_id': 'ninja://sample/test:some_test/TestSuite.Test0',
              'variant_hash': '0hash',
              'tags': '[{"key":"step_name","value":"some test (with patch)"}]',
              'invocation': ['invocation/1']
          }])),
      api.resultdb.get_test_result_history(
          res,
          step_name=(
              'searching_for_new_tests.'
              'cross reference newly identified tests against ResultDB')),
      api.post_process(
          post_process.StepCommandContains,
          ('searching_for_new_tests.'
           'cross reference newly identified tests against ResultDB'), [
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
          check_for_flakiness=False,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'non-existent-try-builder',
      api.buildbucket.try_build(
          'chromium',
          'mac',
          git_repo='https://chromium.googlesource.com/chromium/src',
          change_number=91827,
          patch_set=1),
      api.flakiness(
          check_for_flakiness=True,
          build_count=10,
          historical_query_count=2,
          current_query_count=2,
      ),
      api.override_step_data(
          'searching_for_new_tests.gsutil download', retcode=1),
      api.post_process(
          post_process.StepTextEquals, 'searching_for_new_tests',
          'The current try builder may not have test data precomputed.'),
      api.post_process(post_process.DoesNotRunRE, '.*unpack.*',
                       '.*process precomputed test history.*'),
      api.post_process(post_process.DropExpectation),
  )

# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb2

DEPS = [
    'flakiness',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/properties',
]


def RunSteps(api):
  inv_list = ['invocations/2', 'invocations/3', 'invocations/4']

  found_invs = api.flakiness.get_builder_invocation_history(
      builder_id=builder_pb2.BuilderID(builder='Builder'),
      excluded_invs=api.properties.get('excluded_invs'))
  api.assertions.assertEqual(inv_list, found_invs)


def GenTests(api):
  build_database = []
  for i in range(5):
    inv = "invocations/{}".format(i + 1)
    build = build_pb2.Build(
        id=i + 1,
        builder=builder_pb2.BuilderID(builder='Builder'),
        infra=build_pb2.BuildInfra(
            resultdb=build_pb2.BuildInfra.ResultDB(invocation=inv)),
    )
    build_database.append(build)

  yield api.test(
      'basic',
      api.flakiness(identify_new_tests=True, build_count=5),
      api.buildbucket.build(build_database[0]),
      api.properties(excluded_invs={'invocations/1', 'invocations/5'}),
      api.buildbucket.simulated_search_results(
          builds=build_database, step_name='get_historical_invocations'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no excluded invocations',
      api.flakiness(identify_new_tests=True, build_count=3),
      api.buildbucket.build(build_database[0]),
      api.properties(excluded_invs=None),
      api.buildbucket.simulated_search_results(
          builds=build_database[1:4], step_name='get_historical_invocations'),
      api.post_process(post_process.DropExpectation),
  )

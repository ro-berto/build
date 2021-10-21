# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'flakiness',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/step',
]


def RunSteps(api):
  invocations = api.flakiness.fetch_all_related_invocations()
  for inv in invocations:
    api.assertions.assertEqual(type(inv), str)

  api.assertions.assertEqual(invocations, {'invocations/1'})


def GenTests(api):
  basic_build = build_pb2.Build(
      id=1,
      infra=build_pb2.BuildInfra(
          resultdb=build_pb2.BuildInfra.ResultDB(invocation='invocations/1')),
      input=build_pb2.Build.Input(gerrit_changes=[
          common_pb2.GerritChange(
              host='chromium-review.googlesource.com',
              project='chromium/src',
              change=10,
              patchset=3,
          )
      ]),
  )

  yield api.test(
      'basic', api.flakiness(check_for_flakiness=True),
      api.buildbucket.build(basic_build),
      api.buildbucket.simulated_search_results(
          builds=[basic_build],
          step_name='fetching associated builds with current gerrit patchset'),
      api.post_process(
          post_process.StepCommandContains,
          'fetching associated builds with current gerrit patchset',
          [
              "-predicate",
              "{\"builder\": {}, \"gerritChanges\": [{\"change\": \"10\","
              " \"host\": \"chromium-review.googlesource.com\", \"patchset\": "
              "\"1\", \"project\": \"chromium/src\"}]}", "-predicate",
              "{\"builder\": {}, \"gerritChanges\": [{\"change\": \"10\", "
              "\"host\": \"chromium-review.googlesource.com\", \"patchset\": "
              "\"2\", \"project\": \"chromium/src\"}]}", "-predicate",
              "{\"builder\": {}, \"gerritChanges\": [{\"change\": \"10\", "
              "\"host\": \"chromium-review.googlesource.com\", \"patchset\": "
              "\"3\", \"project\": \"chromium/src\"}]}"
          ],
      ), api.post_process(post_process.DropExpectation))

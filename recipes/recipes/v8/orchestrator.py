# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Orchestrator recipe.

Trigger the compilator to perform all check-out-related tasks and streams
its steps. Afterwards perform testing based on compilator properties.

The orchestrator is only used in a trybot setting.
"""

import json

from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from PB.recipe_engine import result as result_pb2

from recipe_engine.post_process import (
    DoesNotRun, DropExpectation, MustRun, ResultReason, StatusException,
    StatusFailure)
from recipe_engine.recipe_api import Property

from google.protobuf import json_format
from google.protobuf import struct_pb2

DEPS = [
  'depot_tools/gitiles',
  'depot_tools/tryserver',
  'isolate',
  'recipe_engine/buildbucket',
  'recipe_engine/cipd',
  'recipe_engine/json',
  'recipe_engine/properties',
  'recipe_engine/step',
  'recipe_engine/swarming',
  'v8_tests',
]

PROPERTIES = {
    # Name of the compilator trybot to use.
    'compilator_name': Property(kind=str),
}


# TODO(https://crbug.com/890222): Implement cancellation logic.
def RunSteps(api, compilator_name):
  v8 = api.v8_tests

  with api.step.nest('initialization'):
    # Start compilator build.
    request = api.buildbucket.schedule_request(
        builder=compilator_name,
        swarming_parent_run_id=api.swarming.task_id,
        tags=api.buildbucket.tags(**{'hide-in-gerrit': 'pointless'}))
    build = api.buildbucket.schedule(
        [request], step_name='trigger compilator')[0]

    # Initialize V8 testing.
    v8.set_config('v8')
    v8.load_static_test_configs()

    api.swarming.ensure_client()
    v8.set_up_swarming()

  # Wait for compilator build to complete and stream steps.
  sub_build = launch_compilator_watcher(api, build)
  if 'compilator_properties' not in sub_build.output.properties:
    return result_pb2.RawResult(
        status=sub_build.status, summary_markdown=sub_build.summary_markdown)

  # Initialize the test specs the compilator retrieved from the checkout.
  comp_props = sub_build.output.properties['compilator_properties']
  tests = v8.extra_tests_from_properties(
      {'parent_test_spec': dict(comp_props['parent_test_spec'])})

  if not tests:
    # Running a testing trybot that doesn't specify tests might point to
    # a configuration error.
    return result_pb2.RawResult(
        status=common_pb.FAILURE, summary_markdown='No tests specified')

  # Run tests and initialize other configs needed for testing. GN args
  # from compilation to show on test failures and CAS digests of isolated
  # build artifacts to set up swarming tasks.
  v8.gn_args = list(comp_props['gn_args'])
  v8.isolated_tests = dict(comp_props['swarm_hashes'])
  test_results = v8.runtests(tests)

  if test_results.has_failures:
    # Let tryjobs fail for failures only.
    raise api.step.StepFailure('Failures in tryjob.')


def launch_compilator_watcher(api, build):
  """Follow the ongoing compilator build and stream the steps into this build."""
  cipd_pkg = 'infra/chromium/compilator_watcher/${platform}'
  compilator_watcher = api.cipd.ensure_tool(cipd_pkg, 'latest')

  sub_build = build_pb2.Build()
  sub_build.CopyFrom(build)
  cmd = [
      compilator_watcher,
      '--',
      '-compilator-id',
      build.id,
      '-get-swarming-trigger-props'
  ]

  build_url = api.buildbucket.build_url(build_id=build.id)
  build_link = f'compilator build: {build.id}'

  try:
    ret = api.step.sub_build('compilator steps', cmd, sub_build)
    ret.presentation.links[build_link] = build_url
    return ret.step.sub_build
  except api.step.StepFailure:
    ret = api.step.active_result
    ret.presentation.links[build_link] = build_url
    sub_build = ret.step.sub_build
    if not sub_build:
      raise api.step.InfraFailure('sub_build missing from step')
    return sub_build


def GenTests(api):
  def subbuild_data(
      output_properties, summary='', status=common_pb.SUCCESS):
    output_properties = output_properties or {}
    sub_build = build_pb2.Build(
        id=54321,
        status=status,
        summary_markdown=summary,
        output=dict(
            properties=json_format.Parse(
                api.json.dumps(output_properties), struct_pb2.Struct())))
    return api.step_data('compilator steps', api.step.sub_build(sub_build))

  # Minimal v8-side test spec for simulating most recipe features.
  test_spec = json.dumps({
    "tests": [
      {"name": "v8testing"},
      {"name": "test262_variants", "test_args": ["--extra-flags=--flag"]},
    ],
  }, indent=2)
  parent_test_spec = api.v8_tests.example_parent_test_spec_properties(
      'v8_foobar_rel_ng_triggered', test_spec)

  # Dummy CAS digest hashes.
  buider_spec = parent_test_spec.get('parent_test_spec', {})
  swarm_hashes = api.v8_tests._make_dummy_swarm_hashes(
      test[0] for test in buider_spec.get('tests', []))

  # Dummy GN args from compilation.
  gn_args = ['use_foo = true', 'also_interesting = "absolutely"']

  # Set up compilator build output.
  output_properties = {
    "compilator_properties": {
        "swarm_hashes": swarm_hashes,
        "gn_args": gn_args,
        **parent_test_spec,
    },
  }

  def test(name, *args):
    return api.test(
        name, api.buildbucket.try_build(builder='v8_foobar_rel'),
        api.properties(compilator_name='v8_foobar_compile_rel'), *args)

  yield test(
      'basic',
      subbuild_data(output_properties),
      api.step_data('Check', api.v8_tests.one_failure()),
      api.post_process(MustRun, 'Check'),
      api.post_process(MustRun, 'Test262'),

  )

  yield test(
      'missing_properties',
      subbuild_data({}, 'Compile failed', common_pb.FAILURE),
      api.post_process(DoesNotRun, 'Check'),
      api.post_process(DoesNotRun, 'Test262'),
      api.post_process(ResultReason, 'Compile failed'),
      api.post_process(StatusFailure),
      api.post_process(DropExpectation),
  )

  yield test(
      'infra_failure',
      subbuild_data({}, 'Timeout', common_pb.INFRA_FAILURE),
      api.post_process(DoesNotRun, 'Check'),
      api.post_process(DoesNotRun, 'Test262'),
      api.post_process(ResultReason, 'Timeout'),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield test(
      'no_subbuild',
      api.post_process(ResultReason, 'sub_build missing from step'),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield test(
      'no_tests',
      subbuild_data({'compilator_properties': {'parent_test_spec': {}}}),
      api.post_process(DoesNotRun, 'Check'),
      api.post_process(DoesNotRun, 'Test262'),
      api.post_process(ResultReason, 'No tests specified'),
      api.post_process(StatusFailure),
      api.post_process(DropExpectation),
  )

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
from PB.recipe_modules.recipe_engine.led import properties as led_properties_pb

from recipe_engine.post_process import (
    DoesNotRun, DropExpectation, MustRun, ResultReason, StatusException,
    StatusFailure, StatusSuccess)
from recipe_engine.recipe_api import Property

from google.protobuf import json_format
from google.protobuf import struct_pb2

DEPS = [
  'depot_tools/gitiles',
  'depot_tools/tryserver',
  'isolate',
  'recipe_engine/buildbucket',
  'recipe_engine/cipd',
  'recipe_engine/file',
  'recipe_engine/json',
  'recipe_engine/led',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/runtime',
  'recipe_engine/step',
  'recipe_engine/swarming',
  'v8_tests',
]

PROPERTIES = {
    # Name of the compilator trybot to use.
    'compilator_name': Property(kind=str),
}

BUILD_CANCELED_SUMMARY = 'Build was canceled.'
BUILD_WRONGLY_CANCELED_SUMMARY = (
    'Compilator was canceled before the parent orchestrator was canceled.')


def orchestrator_steps(api, compilator_name):
  v8 = api.v8_tests
  compilator_handler = create_compilator_handler(api, compilator_name)

  with api.step.nest('initialization'):
    # Start compilator build.
    build = compilator_handler.trigger_compilator()

    # Initialize V8 testing.
    v8.set_config('v8')
    v8.read_cl_footer_flags()
    v8.load_static_test_configs()

    api.swarming.ensure_client()
    v8.set_up_swarming()

  # Wait for compilator build to complete and stream steps.
  sub_build = compilator_handler.launch_compilator_watcher(build)

  # This condition should be rare as swarming only propagates
  # cancelations from parent -> child.
  if sub_build.status == common_pb.CANCELED:
    if api.runtime.in_global_shutdown:
      return result_pb2.RawResult(
          status=common_pb.CANCELED, summary_markdown=BUILD_CANCELED_SUMMARY)
    raise api.step.InfraFailure(BUILD_WRONGLY_CANCELED_SUMMARY)

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


def RunSteps(api, compilator_name):
  try:
    return orchestrator_steps(api, compilator_name)
  finally:
    if api.runtime.in_global_shutdown:
      # pylint: disable=lost-exception
      # Cancellation can cause all sorts of spurious exceptions.
      return result_pb2.RawResult(
          status=common_pb.CANCELED,
          summary_markdown=BUILD_CANCELED_SUMMARY)


def create_compilator_handler(api, compilator_name):
  if api.led.launched_by_led:
    return LedCompilatorHandler(api, compilator_name)
  return ProdCompilatorHandler(api, compilator_name)


class CompilatorHandler:

  def __init__(self, api, compilator_name):
    self.api = api
    self.compilator_name = compilator_name


class ProdCompilatorHandler(CompilatorHandler):
  def trigger_compilator(self):
    """Trigger a compilator build via buildbucket."""
    request = self.api.buildbucket.schedule_request(
        builder=self.compilator_name,
        swarming_parent_run_id=self.api.swarming.task_id,
        tags=self.api.buildbucket.tags(**{'hide-in-gerrit': 'pointless'}))
    return self.api.buildbucket.schedule(
        [request], step_name='trigger compilator')[0]

  def launch_compilator_watcher(self, build_handle):
    """Follow the ongoing compilator build and stream the steps into this
    build.
    """
    cipd_pkg = 'infra/chromium/compilator_watcher/${platform}'
    compilator_watcher = self.api.cipd.ensure_tool(cipd_pkg, 'latest')

    sub_build = build_pb2.Build()
    sub_build.CopyFrom(build_handle)
    cmd = [
        compilator_watcher,
        '--',
        '-compilator-id',
        build_handle.id,
        '-get-swarming-trigger-props'
    ]

    build_url = self.api.buildbucket.build_url(build_id=build_handle.id)
    build_link = f'compilator build: {build_handle.id}'

    try:
      ret = self.api.step.sub_build('compilator steps', cmd, sub_build)
      ret.presentation.links[build_link] = build_url
      return ret.step.sub_build
    except self.api.step.StepFailure as e:
      ret = self.api.step.active_result
      ret.presentation.links[build_link] = build_url
      sub_build = ret.step.sub_build
      if not sub_build:
        raise self.api.step.InfraFailure('sub_build missing from step') from e
      return sub_build


class LedCompilatorHandler(CompilatorHandler):
  def trigger_compilator(self):
    """Trigger a compilator build via led."""
    project=self.api.buildbucket.build.builder.project
    bucket=self.api.buildbucket.build.builder.bucket
    led_builder_id = f'luci.{project}.{bucket}:{self.compilator_name}'
    with self.api.step.nest('trigger compilator'):
      led_job = self.api.led('get-builder', led_builder_id)
      led_job = self.api.led.inject_input_recipes(led_job)

      gerrit_change = self.api.tryserver.gerrit_change
      gerrit_cl_url = (
          f'https://{gerrit_change.host}/c/{gerrit_change.project}/+/'
          f'{gerrit_change.change}/{gerrit_change.patchset}')
      led_job = led_job.then('edit-cr-cl', gerrit_cl_url)

      return led_job.then('launch').launch_result

  def launch_compilator_watcher(self, build_handle):
    """Collect the compilator led build from swarming. Streaming steps as in
    production is not available.
    """
    output_dir = self.api.path.mkdtemp()
    self.api.swarming.collect(
        'collect led compilator build',
        [build_handle.task_id],
        output_dir=output_dir)

    build_json = self.api.file.read_json(
        'read build.proto.json',
        output_dir.join(build_handle.task_id, 'build.proto.json'),
    )
    return json_format.ParseDict(
        build_json, build_pb2.Build(), ignore_unknown_fields=True)


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
    'swarming_task_attrs': {
      'priority': 25,
      'expiration': 1200,
      'hard_timeout': 3600,
    },
    "tests": [
      {"name": "v8testing"},
      {"name": "test262", "test_args": ["--extra-flags=--flag"]},
    ],
  }, indent=2)
  parent_test_spec = api.v8_tests.example_parent_test_spec_properties(
      'v8_foobar_rel', test_spec)

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
      'testing_canceled',
      subbuild_data(output_properties),
      api.runtime.global_shutdown_on_step('Check'),
      api.post_process(ResultReason, BUILD_CANCELED_SUMMARY),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield test(
      'subbuild_canceled',
      api.runtime.global_shutdown_on_step('compilator steps'),
      subbuild_data({}, '', common_pb.CANCELED),
      api.post_process(ResultReason, BUILD_CANCELED_SUMMARY),
      api.post_process(StatusException),
      api.post_process(DropExpectation),
  )

  yield test(
      'subbuild_canceled_before_parent',
      subbuild_data({}, '', common_pb.CANCELED),
      api.post_process(ResultReason, BUILD_WRONGLY_CANCELED_SUMMARY),
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

  led_properties = {
      '$recipe_engine/led':
          led_properties_pb.InputProperties(
              led_run_id='fake-run-id',
          ),
  }

  build_proto_json = {
    'status': common_pb.SUCCESS,
    'summary': '',
    'output': {
      'properties': output_properties,
    },
  }

  yield test(
      'run_with_led',
      api.properties(**led_properties),
      api.step_data(
          'read build.proto.json',
          api.file.read_json(json_content=build_proto_json)),
      api.post_process(MustRun, 'initialization.trigger compilator.led get-builder'),
      api.post_process(MustRun, 'initialization.trigger compilator.led edit-cr-cl'),
      api.post_process(MustRun, 'initialization.trigger compilator.led launch'),
      api.post_process(MustRun, 'collect led compilator build'),
      api.post_process(MustRun, 'read build.proto.json'),
      api.post_process(MustRun, 'Check'),
      api.post_process(MustRun, 'Test262'),
      api.post_process(StatusSuccess),
      api.post_process(DropExpectation),
  )

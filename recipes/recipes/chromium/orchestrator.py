# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Triggers compilator and tests"""

from recipe_engine import post_process
from PB.recipes.build.chromium.orchestrator import InputProperties
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from google.protobuf import json_format
from google.protobuf import struct_pb2

DEPS = [
    'builder_group',
    'chromium',
    'chromium_swarming',
    'chromium_tests',
    'chromium_tests_builder_config',
    'isolate',
    'recipe_engine/buildbucket',
    'recipe_engine/json',
    'recipe_engine/properties',
    'recipe_engine/step',
    'recipe_engine/swarming',
    'test_utils',
]

PROPERTIES = InputProperties


def RunSteps(api, properties):
  if not properties.compilator:
    raise api.step.InfraFailure('Missing compilator input')

  with api.chromium.chromium_layout():
    # Scheduled build inherits current build's project and bucket
    request = api.buildbucket.schedule_request(
        builder=properties.compilator,
        swarming_parent_run_id=api.swarming.task_id,
        properties={
            'orchestrator': {
                'builder_name': api.buildbucket.builder_name,
                'builder_group': api.builder_group.for_current
            }
        },
        tags=api.buildbucket.tags(**{'hide-in-gerrit': 'pointless'}))

    build = api.buildbucket.schedule([request],
                                     step_name='trigger compilator')[0]

    builder_id, builder_config = (
        api.chromium_tests_builder_config.lookup_builder())

    api.chromium_tests.configure_build(builder_config)
    api.chromium_tests.report_builders(builder_config)

    _, targets_config = api.chromium_tests.prepare_checkout(
        builder_config,
        timeout=3600,
        set_output_commit=builder_config.set_output_commit,
        no_fetch_tags=True)

    build = api.buildbucket.collect_builds([build.id],
                                           interval=20,
                                           timeout=7200,
                                           step_name='collect compilator',
                                           mirror_status=True)[build.id]

    if 'swarming_trigger_properties' not in build.output.properties:
      # No tests to trigger
      return

    swarming_props = build.output.properties['swarming_trigger_properties']

    swarming_digest = swarming_props['swarming_command_lines_digest']
    swarming_cwd = swarming_props['swarming_command_lines_cwd']

    swarm_hashes = swarming_props['swarm_hashes']
    swarm_hashes = dict(zip(swarm_hashes.keys(), swarm_hashes.values()))
    assert api.isolate.isolated_tests == {}
    api.isolate.set_isolated_tests(swarm_hashes)

    tests = [
        t for t in targets_config.all_tests()
        if t.uses_isolate and t.target_name in api.isolate.isolated_tests
    ]
    api.chromium_tests.download_command_lines_for_tests(
        tests,
        builder_config,
        swarming_command_lines_digest=swarming_digest,
        swarming_command_lines_cwd=swarming_cwd)

    api.chromium_tests.configure_swarming(False, builder_group=builder_id.group)
    test_runner = api.chromium_tests.create_test_runner(
        tests,
        suffix='with patch',
        serialize_tests=builder_config.serialize_tests,
        retry_failed_shards=True,
        # If any tests export coverage data we want to retry invalid shards due
        # to an existing issue with occasional corruption of collected coverage
        # data.
        retry_invalid_shards=any(
            t.runs_on_swarming and t.isolate_profile_data for t in tests),
    )

    with api.chromium_tests.wrap_chromium_tests(builder_config, tests):
      return test_runner()


def GenTests(api):

  def override_test_spec():
    return api.chromium_tests.read_source_side_spec(
        'chromium.linux', {
            'Linux Builder': {
                'scripts': [{
                    "isolate_profile_data": True,
                    "name": "check_static_initializers",
                    "script": "check_static_initializers.py",
                    "swarming": {}
                }],
            },
            'Linux Tests': {
                'gtest_tests': [{
                    'name': 'browser_tests',
                    'swarming': {
                        'can_use_on_swarming_builders': True
                    },
                }]
            },
        })

  def override_compilator():
    fake_command_lines_digest = (
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855/0')
    swarming_trigger_propertes = {
        'swarming_command_lines_digest': fake_command_lines_digest,
        'swarming_command_lines_cwd': 'out/Release',
        'swarm_hashes': {
            'browser_tests': '07de23bcf07fe2d5babb5140f727f6e53dbc1d1a'
        },
    }
    return api.buildbucket.simulated_collect_output(
        [
            build_pb2.Build(
                id=8922054662172514000,
                output=dict(
                    properties=json_format.Parse(
                        api.json.dumps({
                            'swarming_trigger_properties':
                                swarming_trigger_propertes
                        }), struct_pb2.Struct())))
        ],
        step_name='collect compilator')

  yield api.test(
      'basic',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      override_test_spec(),
      override_compilator(),
      api.post_process(post_process.MustRun, 'trigger compilator'),
      api.post_process(post_process.MustRun, 'collect compilator'),
      api.post_process(post_process.LogContains, 'trigger compilator',
                       'request',
                       ['tryserver.chromium.linux', 'linux-rel-compilator']),
      api.post_process(post_process.MustRun, 'browser_tests (with patch)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )
  yield api.test(
      'no_tests_to_trigger',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      override_test_spec(),
      api.buildbucket.simulated_collect_output([
          build_pb2.Build(
              id=8922054662172514000,
              output=dict(
                  properties=json_format.Parse(
                      api.json.dumps({}), struct_pb2.Struct())))
      ],
                                               step_name='collect compilator'),
      api.post_process(post_process.MustRun, 'trigger compilator'),
      api.post_process(post_process.MustRun, 'collect compilator'),
      api.post_process(post_process.LogContains, 'trigger compilator',
                       'request',
                       ['tryserver.chromium.linux', 'linux-rel-compilator']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'no_builder_to_trigger_passed_in',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.post_process(post_process.DoesNotRun, 'trigger compilator'),
      api.post_process(post_process.DoesNotRun, 'collect compilator'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failing_test_retry_shard_passed',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      override_test_spec(),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(True), failure=False)),
      override_compilator(),
      api.post_process(post_process.MustRun, 'trigger compilator'),
      api.post_process(post_process.MustRun, 'collect compilator'),
      api.post_process(post_process.MustRun,
                       'browser_tests (retry shards with patch)'),
      api.post_process(post_process.LogContains, 'trigger compilator',
                       'request',
                       ['tryserver.chromium.linux', 'linux-rel-compilator']),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'failing_test_retry_shard_failed',
      api.chromium.try_build(builder='linux-rel-orchestrator'),
      api.properties(InputProperties(compilator='linux-rel-compilator')),
      override_test_spec(),
      api.override_step_data(
          'browser_tests (with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      api.override_step_data(
          'browser_tests (retry shards with patch)',
          api.chromium_swarming.canned_summary_output(
              api.test_utils.canned_gtest_output(False), failure=True)),
      override_compilator(),
      api.post_process(post_process.MustRun, 'trigger compilator'),
      api.post_process(post_process.MustRun, 'collect compilator'),
      api.post_process(post_process.MustRun,
                       'browser_tests (retry shards with patch)'),
      api.post_process(post_process.LogContains, 'trigger compilator',
                       'request',
                       ['tryserver.chromium.linux', 'linux-rel-compilator']),
      api.post_process(post_process.StatusFailure),
      api.post_process(post_process.DropExpectation),
  )
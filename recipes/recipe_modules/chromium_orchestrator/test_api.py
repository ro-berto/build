# Copyright 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api
from PB.go.chromium.org.luci.buildbucket.proto import build as build_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb
from google.protobuf import struct_pb2
from google.protobuf import json_format

from RECIPE_MODULES.build.chromium_tests.api import (
    ALL_TEST_BINARIES_ISOLATE_NAME)


class ChromiumOrchestratorApi(recipe_test_api.RecipeTestApi):

  def override_test_spec(self,
                         builder_group,
                         builder,
                         tester=None,
                         tests=None,
                         shards=1,
                         step_suffix=None):
    """Override spec for the builder(s) mirrored by an orchestrator.

    Args:
      builder_group: The group of the builder that is mirrored.
      builder: The name of the builder that is mirrored.
      tester: The name of the tester that is mirrored. If not specified,
        swarming tests will be set for the builder.
      tests: The set of swarming tests that should be on the tester.
      shards: The number of shards for the swarming tests.
    """
    source_side_spec = {
        builder: {
            'scripts': [{
                "isolate_profile_data": True,
                "name": "check_static_initializers",
                "script": "check_static_initializers.py",
                "swarming": {}
            }],
        },
    }

    tests = tests or ['browser_tests']
    gtest_tests = [{
        'name': test,
        'swarming': {
            'can_use_on_swarming_builders': True,
            'shards': shards,
        },
        'isolate_coverage_data': True,
    } for test in tests]
    tester_dict = source_side_spec.setdefault(tester or builder, {})
    tester_dict['gtest_tests'] = gtest_tests

    return self.m.chromium_tests.read_source_side_spec(
        builder_group, source_side_spec, step_suffix=step_suffix)

  def get_fake_swarming_trigger_properties(self, tests):
    input_hash = (
        '797e944dad5241e7fe111cfd01e45f02e2f4937dd34b248603e603d2948e174e/1298')
    swarm_hashes = {test: input_hash for test in tests}
    swarm_hashes[ALL_TEST_BINARIES_ISOLATE_NAME] = input_hash
    return {
        'swarming_command_lines_digest':
            'e3b0c44298fc1c149afbfc8996fb92427ae41e4649b934ca495991b7852b855/0',
        'swarming_command_lines_cwd':
            'out/Release',
        'swarm_hashes':
            swarm_hashes,
    }

  def override_compilator_steps(self,
                                comp_build_id=1234,
                                sub_build_status=common_pb.SUCCESS,
                                sub_build_summary='',
                                empty_props=False,
                                is_swarming_phase=True,
                                with_patch=True,
                                tests=None,
                                affected_files=None,
                                src_side_deps_digest=None):
    tests = tests or ['browser_tests']
    output_json_obj = {}
    if is_swarming_phase:
      if not empty_props:
        output_json_obj = {
            'swarming_trigger_properties':
                self.get_fake_swarming_trigger_properties(tests),
            'got_angle_revision':
                '18c36f8aa629231795c82831a2cf80e8f77f989a',
            'got_revision':
                '6eb925582a36cdba74ad60f01a19897866a92cca',
            'got_revision_cp':
                'refs/heads/main@{#984947}',
            'got_v8_revision':
                '7d776826a3c4ae0878f026c00beab82765fb4d23',
        }
        if with_patch:
          if not affected_files:
            affected_files = [
                'src/ash/root_window_controller.cc',
                'src/ash/root_window_controller.h',
                'src/deleted_file.cc',
            ]

          output_json_obj.update({
              'affected_files': {
                  'first_100': affected_files,
                  'total_count': 3
              },
              'deleted_files': ['src/deleted_file.cc'],
          })
        if src_side_deps_digest:
          output_json_obj['src_side_deps_digest'] = src_side_deps_digest

    sub_build = build_pb2.Build(
        id=54321,
        status=sub_build_status,
        summary_markdown=sub_build_summary,
        output=dict(
            properties=json_format.Parse(
                self.m.json.dumps(output_json_obj), struct_pb2.Struct())))
    if with_patch:
      name = 'compilator steps (with patch)'
    else:
      name = 'compilator steps (without patch)'
    if not is_swarming_phase:
      name += ' (2)'
    return self.step_data(
        name,
        self.m.step.sub_build(sub_build),
    )

  def fake_head_revision(self, ref='refs/heads/main'):
    result = {'log': [{'commit': 'deadbeef'},]}
    return self.step_data('read src HEAD revision at {}'.format(ref),
                          self.m.json.output(result))

  def override_schedule_compilator_build(
      self, step_name='trigger compilator (with patch)', build_id=12345):
    return self.m.buildbucket.simulated_schedule_output(
        step_name=step_name,
        batch_response=builds_service_pb2.BatchResponse(
            responses=[dict(schedule_build=build_pb2.Build(id=build_id))]))

  def override_compilator_build_proto_fetch(self,
                                            build_id=12345,
                                            status=common_pb.SUCCESS):
    fake_build = build_pb2.Build(
        id=build_id,
        status=status,
        infra=build_pb2.BuildInfra(
            swarming=build_pb2.BuildInfra.Swarming(task_id='57d9108e76b91310')))
    return self.m.buildbucket.simulated_get(
        build=fake_build,
        step_name='fetch compilator build proto',
    )

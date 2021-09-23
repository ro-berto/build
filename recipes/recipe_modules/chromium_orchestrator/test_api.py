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

  def override_test_spec(self, tests=None, shards=1):
    tests = tests or ['browser_tests']
    gtest_tests = [{
        'name': test,
        'swarming': {
            'can_use_on_swarming_builders': True,
            'shards': shards,
        },
        'isolate_coverage_data': True,
    } for test in tests]
    return self.m.chromium_tests.read_source_side_spec(
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
                'gtest_tests': gtest_tests
            },
        })

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
                                tests=None):
    tests = tests or ['browser_tests']
    output_json_obj = {}
    if is_swarming_phase:
      if not empty_props:
        output_json_obj = {
            'swarming_trigger_properties':
                self.get_fake_swarming_trigger_properties(tests)
        }

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
    return self.override_step_data(
        name,
        self.m.step.sub_build(sub_build),
    )

  def fake_head_revision(self, ref='refs/heads/main'):
    return self.step_data('read src HEAD revision at {}'.format(ref),
                          self.m.gitiles.make_log_test_data('deadbeef'))

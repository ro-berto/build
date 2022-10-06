# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import base64

from google.protobuf import json_format
from collections import defaultdict

from recipe_engine import recipe_api

from RECIPE_MODULES.build.chromium_tests.resultdb import ResultDB

from PB.go.chromium.org.luci.buildbucket.proto \
  import builder_common as builder_common_pb2
from PB.go.chromium.org.luci.buildbucket.proto import (builds_service as
                                                       builds_service_pb2)
from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2

from . import structs

# Skylab prioritizes tests by the Quota Scheduler account attached in the
# request. We applied account "lacros", which has limited high priority
# quota. It is supposed to grant to the production builders only.
# For fyi builders, we use 'lacros_fyi' which only contains the free quota,
# aka the lowest priority.
QS_ACCOUNT_PROD = 'lacros'
QS_ACCOUNT_FYI = 'lacros_fyi'
CTP_BUILDER = 'cros_test_platform'
CTP_BUILDER_DEV = 'cros_test_platform-dev'
AUTOTEST_NAME_TAST = 'tast.lacros'
AUTOTEST_NAME_TELEMETRY = 'chromium_Telemetry'
AUTOTEST_NAME_CHROMIUM = 'chromium'
CROS_BUCKET = 'gs://chromeos-image-archive/'


def _base64_encode_str(s):
  return base64.b64encode(s.encode('utf-8')).decode('ascii')


class SkylabApi(recipe_api.RecipeApi):
  """Module for issuing commands to Skylab"""

  def __init__(self, **kwargs):
    super(SkylabApi, self).__init__(**kwargs)

  def schedule_suites(self, requests, step_name='schedule skylab tests'):
    """Schedule CrOS autotest suites by invoking the cros_test_platform recipe.

    Translate each skylab test request into a CTP Buildbucket request and call
    Buildbucket's Batch method to schedule them. Each CTP build represents one
    test suite.

    Args:
    * requests (list[SkylabRequest]): List of Autotest suites to schedule.
    * step_name (str): a name of scheduling buildbucket build.

    Returns:
      A dict of CTP build IDs keyed by request_tag(see SkylabRequest).
    """
    # Ensure the crosfleet cipd package is installed
    crosfleet_tool = self.m.cipd.ensure_tool(
        'chromiumos/infra/crosfleet/${platform}', 'prod')

    build_ids_by_tags = defaultdict(lambda: [])
    with self.m.step.nest(step_name) as presentation:
      for s in requests:
        with self.m.step.nest(s.request_tag):
          cmd = [crosfleet_tool, 'run', 'test', '-json']

          cmd.extend(['-board', s.board])

          if s.secondary_board and s.secondary_cros_img:
            cmd.extend(['-secondary-boards', s.secondary_board])
            cmd.extend(['-secondary-images', s.secondary_cros_img])

          if s.bucket:
            cmd.extend(['-bucket', s.bucket])

          cmd.extend(['-pool', s.dut_pool if s.dut_pool else 'DUT_POOL_QUOTA'])

          cmd.extend(['-image', s.cros_img])

          cmd.extend(['-timeout-mins', str(int(s.timeout_sec / 60))])

          cmd.extend([
              '-qs-account', QS_ACCOUNT_FYI
              if 'fyi' in self.m.buildbucket.builder_name else QS_ACCOUNT_PROD
          ])

          assert s.resultdb and s.resultdb.enable, ('Skylab tests should '
                                                    'have resultdb enabled.')
          rdb_str = self.m.json.dumps({
              k: getattr(s.resultdb, k)
              for k in attr.fields_dict(ResultDB)
              if not getattr(s.resultdb, k) in [None, '']
          })

          if s.retries:
            cmd.extend(['-max-retries', str(int(s.retries))])

          test_args = []
          if s.test_args:
            test_args.append(s.test_args)

          test_args.append('resultdb_settings=%s' % _base64_encode_str(rdb_str))

          if s.tast_expr:
            # Due to crbug/1173329, skylab does not support arbitrary tast
            # expressions. As a workaround, we encode test argument which may
            # contain complicated patterns to base64.
            test_args.append('tast_expr_b64=%s' %
                             _base64_encode_str(s.tast_expr))

          if s.test_args:
            test_args.append('test_args_b64=%s' %
                             _base64_encode_str(s.test_args))

          if s.exe_rel_path:
            test_args.append('exe_rel_path=%s' % s.exe_rel_path)

          if s.tast_expr_file:
            test_args.append('tast_expr_file=%s' % s.tast_expr_file)
            if s.tast_expr_key:
              test_args.append('tast_expr_key=%s' % s.tast_expr_key)

          if s.benchmark:
            test_args.append('benchmark=%s' % s.benchmark)

          if s.results_label:
            test_args.append('results_label=%s' % s.results_label)

          if s.story_filter:
            test_args.append('story_filter=%s' % s.story_filter)

          if s.test_shard_map_filename:
            test_args.append('test_shard_map_filename=%s' %
                             s.test_shard_map_filename)

          if s.telemetry_shard_index is not None:
            test_args.append('test_shard_index=%s' % s.telemetry_shard_index)

          if s.lacros_gcs_path:
            cmd.extend(['-lacros-path', s.lacros_gcs_path])

            if s.secondary_board and s.secondary_cros_img:
              cmd.extend(['-secondary-lacros-paths', s.lacros_gcs_path])

          if s.autotest_name:
            autotest_name = s.autotest_name
          elif s.test_type == structs.SKYLAB_TAST_TEST:
            autotest_name = AUTOTEST_NAME_TAST
            if s.bucket and 'chromium' in s.bucket:
              test_args.append('run_private_tests=false')
          elif s.test_type == structs.SKYLAB_TELEMETRY:
            autotest_name = AUTOTEST_NAME_TELEMETRY
          else:
            autotest_name = AUTOTEST_NAME_CHROMIUM

          assert s.shards == 1 or s.test_type == structs.SKYLAB_TAST_TEST, (
              'Only sharding for tast tests are currently supported in Skylab')
          for shard in range(s.shards):
            # Create a request for each shard
            shard_cmd = list(cmd)
            shard_test_args = list(test_args)

            if s.test_type == structs.SKYLAB_TAST_TEST:
              shard_test_args.append('shard_index={}'.format(shard))
              shard_test_args.append('total_shards={}'.format(s.shards))

            shard_cmd.extend(['-test-args', ' '.join(shard_test_args)])
            shard_cmd.append(autotest_name)

            shard_link_name = (
                s.request_tag if shard == 0 else '{0} ({1})'.format(
                    s.request_tag, shard))
            step_result = self.m.step(
                'schedule' if shard == 0 else 'schedule ({})'.format(shard),
                shard_cmd,
                raise_on_failure=False,
                stdout=self.m.json.output(),
                step_test_data=lambda: self.m.json.test_api.output_stream(
                    {"Launches": [{
                        "Build": {
                            "id": str(800),
                        },
                    }]}))

            if step_result.retcode == 0:
              shard_build_id = int(
                  step_result.stdout["Launches"][0]["Build"]["id"])
              presentation.links[
                  shard_link_name] = 'https://ci.chromium.org/b/%s' % shard_build_id

              build_ids_by_tags[s.request_tag].append(shard_build_id)

    return build_ids_by_tags

  def wait_on_suites(self, ctp_builds_by_tag, timeout_seconds):
    """Wait for the CTP builds to complete and return their test runner builds.

    Args:
      ctp_builds_by_tag: A dict of CTP build IDs (a list), keyed by request tag.
      timeout_seconds: How long to wait for results before
        giving up.

    Returns:
      A dict of request tag to dict of CTP build (the shard request) to list of
        test_runner attempts
    """
    with self.m.step.nest('collect skylab results'):
      # collect_builds() may hit timeout, but it does not mean
      # all tests are aborted. Some tests may still have exported
      # results to RDB. So an exception or failure here should not
      # block following steps.
      all_build_ids = []
      for ids in ctp_builds_by_tag.values():
        all_build_ids += ids
      try:
        self.m.buildbucket.collect_builds(
            all_build_ids, timeout=timeout_seconds)
      except self.m.step.StepFailure:
        pass
    # TODO(crbug.com/1245438): Remove below once the test runner's invocation
    # is included into its parent build's invocation.
    with self.m.step.nest('find test runner build'):
      test_runners_by_tag = {}
      for test_suite, shard_ctp_build_ids in ctp_builds_by_tag.items():
        # For each shard's CTP build, get any attempts (runner builds)
        for shard_ctp_build_id in shard_ctp_build_ids:
          builds = self.m.buildbucket.search(
              builds_service_pb2.BuildPredicate(
                  builder=builder_common_pb2.BuilderID(
                      project='chromeos',
                      bucket='test_runner',
                      builder='test_runner',
                  ),
                  tags=[
                      common_pb2.StringPair(
                          key='parent_buildbucket_id',
                          value=str(shard_ctp_build_id))
                  ],
                  include_experimental=self.m.runtime.is_experimental))
          if test_suite not in test_runners_by_tag:
            test_runners_by_tag[test_suite] = {}
          test_runners_by_tag[test_suite][shard_ctp_build_id] = builds

    return test_runners_by_tag

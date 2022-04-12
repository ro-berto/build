# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import base64

from google.protobuf import json_format

from recipe_engine import recipe_api

from RECIPE_MODULES.build.chromium_tests.resultdb import ResultDB

from PB.go.chromium.org.luci.buildbucket.proto import builder as builder_pb2
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
      A dict of CTP build ID keyed by request_tag(see SkylabRequest).
    """
    # Ensure the crosfleet cipd package is installed
    # TODO(crbug.com/1273634): We need to pin the version of crosfleet to use.
    crosfleet_tool = self.m.cipd.ensure_tool(
        'chromiumos/infra/crosfleet/${platform}', 'latest')

    build_id_by_tags = {}
    with self.m.step.nest(step_name) as presentation:
      for i, s in enumerate(requests):
        with self.m.step.nest(s.request_tag):
          cmd = [crosfleet_tool, 'run', 'test', '-json']

          cmd.extend(['-board', s.board])

          if s.secondary_board and s.secondary_cros_img:
            cmd.extend(['-secondary-boards', s.secondary_board])
            cmd.extend(['-secondary-images', s.secondary_cros_img])

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

          cmd.extend(['-test-args', ' '.join(test_args)])

          if s.lacros_gcs_path:
            cmd.extend(['-lacros-path', s.lacros_gcs_path])

            if s.secondary_board and s.secondary_cros_img:
              cmd.extend(['-secondary-lacros-paths', s.lacros_gcs_path])

          if s.autotest_name:
            autotest_name = s.autotest_name
          elif s.test_type == structs.SKYLAB_TAST_TEST:
            autotest_name = AUTOTEST_NAME_TAST
          else:
            autotest_name = AUTOTEST_NAME_CHROMIUM
          cmd.append(autotest_name)

          step_result = self.m.step(
              'schedule',
              cmd,
              stdout=self.m.json.output(),
              step_test_data=lambda: self.m.json.test_api.output_stream(
                  {"Launches": [{
                      "Build": {
                          "id": str(800 + i),
                      },
                  }]}))

          build_id_by_tags[s.request_tag] = int(
              step_result.stdout["Launches"][0]["Build"]["id"])
          presentation.links[(
              s.request_tag
          )] = 'https://ci.chromium.org/b/%s' % build_id_by_tags[s.request_tag]
    return build_id_by_tags

  def wait_on_suites(self, ctp_by_tag, timeout_seconds):
    """Wait for the CTP builds to complete and return their test runner builds.

    Args:
      ctp_by_tag: A dict of CTP build ID, keyed by request tag.
      timeout_seconds: How long to wait for results before
        giving up.

    Returns:
      A dict of test runner builds with the key of request tag.
    """
    with self.m.step.nest('collect skylab results'):
      # collect_builds() may hit timeout, but it does not mean
      # all tests are aborted. Some tests may still have exported
      # results to RDB. So an exception or failure here should not
      # block following steps.
      try:
        self.m.buildbucket.collect_builds(
            list(ctp_by_tag.values()), timeout=timeout_seconds)
      except self.m.step.StepFailure:
        pass
    # TODO(crbug.com/1245438): Remove below once the test runner's invocation
    # is included into its parent build's invocation.
    with self.m.step.nest('find test runner build'):
      test_runners_by_tag = {}
      for t, ctp_build_id in ctp_by_tag.items():
        builds = self.m.buildbucket.search(
            builds_service_pb2.BuildPredicate(
                builder=builder_pb2.BuilderID(
                    project='chromeos',
                    bucket='test_runner',
                    builder='test_runner',
                ),
                tags=[
                    common_pb2.StringPair(
                        key='parent_buildbucket_id', value=str(ctp_build_id))
                ],
                include_experimental=self.m.runtime.is_experimental))
        test_runners_by_tag[t] = builds

    return test_runners_by_tag

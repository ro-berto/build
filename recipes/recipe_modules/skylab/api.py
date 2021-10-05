# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import attr
import base64

from google.protobuf import json_format

from recipe_engine import recipe_api

from RECIPE_MODULES.build.chromium_tests.resultdb import ResultDB

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.test_platform.request import Request
from PB.test_platform.steps.execution import ExecuteResponse, ExecuteResponses
from PB.test_platform.taskstate import TaskState

from . import structs

QS_ACCOUNT = 'lacros'
CTP_BUILDER = 'cros_test_platform'
CTP_BUILDER_DEV = 'cros_test_platform-dev'
AUTOTEST_NAME_TAST = 'tast.lacros'
AUTOTEST_NAME_CHROMIUM = 'chromium'
CROS_BUCKET = 'gs://chromeos-image-archive/'
POOL = Request.Params.Scheduling.MANAGED_POOL_QUOTA


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
    build_id_by_tags = {}
    bb_requests = []
    with self.m.step.nest(step_name) as presentation:
      for s in requests:
        with self.m.step.nest(s.request_tag):
          req = Request()
          gs_img_uri = CROS_BUCKET + s.cros_img
          req.params.metadata.test_metadata_url = gs_img_uri
          req.params.metadata.debug_symbols_archive_url = gs_img_uri
          sw_dep = req.params.software_dependencies.add()
          sw_dep.chromeos_build = s.cros_img
          req.params.scheduling.qs_account = QS_ACCOUNT
          req.params.software_attributes.build_target.name = s.board
          req.params.time.maximum_duration.seconds = s.timeout_sec
          autotest_to_create = req.test_plan.test.add()
          autotest_name = AUTOTEST_NAME_CHROMIUM
          if s.test_type == structs.SKYLAB_TAST_TEST:
            autotest_name = AUTOTEST_NAME_TAST
          autotest_to_create.autotest.name = autotest_name
          tags = {
              'label-board': s.board,
              'build': gs_img_uri,
              'suite': autotest_name,
          }
          test_args = ['dummy=crbug.com/984103']
          if s.dut_pool:
            req.params.scheduling.unmanaged_pool = s.dut_pool
            tags['label-pool'] = s.dut_pool
          else:
            req.params.scheduling.managed_pool = POOL
            tags['label-pool'] = 'DUT_POOL_QUOTA'
          if s.tast_expr:
            # Due to crbug/1173329, skylab does not support arbitrary tast
            # expressions. As a workaround, we encode test argument which may
            # contain complicated patterns to base64.
            test_args.append('tast_expr_b64=%s' % base64.b64encode(s.tast_expr))
            tags['tast-expr'] = s.tast_expr
          if s.test_args:
            test_args.append('test_args_b64=%s' % base64.b64encode(s.test_args))
            tags['test_args'] = s.test_args
          if s.resultdb and s.resultdb.enable:
            rdb_str = self.m.json.dumps({
                k: getattr(s.resultdb, k)
                for k in attr.fields_dict(ResultDB)
                if not getattr(s.resultdb, k) in [None, '']
            })
            test_args.append('resultdb_settings=%s' % base64.b64encode(rdb_str))
          if s.lacros_gcs_path:
            lacros_dep = req.params.software_dependencies.add()
            lacros_dep.lacros_gcs_path = s.lacros_gcs_path
            tags['lacros_gcs_path'] = s.lacros_gcs_path
          if s.exe_rel_path:
            test_args.append('exe_rel_path=%s' % s.exe_rel_path)
            tags['exe_rel_path'] = s.exe_rel_path
          autotest_to_create.autotest.test_args = ' '.join(test_args)
          swarming_tags = [
              '{}:{}'.format(key, value) for key, value in tags.items()
          ]
          req.params.decorations.tags.extend(swarming_tags)
          if s.retries:
            self._enable_test_retries(req, s.retries)

          # We're sending this only to add a link back to the parent.
          bb_tags = {'parent_buildbucket_id': str(self.m.buildbucket.build.id)}
          bb_requests.append(
              self.m.buildbucket.schedule_request(
                  CTP_BUILDER_DEV
                  if self.m.runtime.is_experimental else CTP_BUILDER,
                  project='chromeos',
                  bucket='testplatform',
                  properties={
                      'requests': {
                          s.request_tag: json_format.MessageToDict(req)
                      },
                  },
                  tags=self.m.buildbucket.tags(**bb_tags),
                  gerrit_changes=[],
                  exe_cipd_version=''))

      builds = self.m.buildbucket.schedule(bb_requests)
      assert len(builds) == len(
          requests), '%d test suites but only got %d builds' % (len(requests),
                                                                len(builds))
      # The buildbucket batch response is guaranteed to keep the same order
      # as its request.
      for b, r in zip(builds, requests):
        # Build.id is int64, implemented in recipe as long.
        # This is safe on a 64bit CPU bot for CTP build ID,
        # e.g. 8863223149660721536.
        build_id_by_tags[r.request_tag] = int(b.id)
        build_url = self.m.buildbucket.build_url(build_id=b.id)
        presentation.links[r.request_tag] = build_url

    return build_id_by_tags

  def wait_on_suites(self, ctp_by_tag, timeout_seconds):
    """Wait for the CTP builds to complete and return their test runner builds.

    Args:
      ctp_by_tag: A dict of CTP build ID, keyed by request tag.
      timeout_seconds: How long to wait for results before
        giving up.

    Returns:
      list[SkylabSuiteResponse]: The results for the provided requests.
    """
    with self.m.step.nest('collect skylab results') as presentation:
      ctp_builds = self.m.buildbucket.collect_builds(
          ctp_by_tag.values(), timeout=timeout_seconds)

      tagged_ctp_resp = {}
      tagged_responses = {}
      for ctp_build in ctp_builds.values():
        tagged_ctp_resp.update(self._get_multi_response_binary(ctp_build))
      for t in tagged_ctp_resp:
        # Note, request tag is mapped to a list of responses, because CTP has
        # retry logic. A single request may have multiple attempts executed.
        tagged_responses[t] = self._translate_result(
            tagged_ctp_resp.get(t, self._default_failed_response()))

      presentation.logs['return value'] = [str(t) for t in tagged_responses]

      return structs.SkylabTaggedResponses.create(
          # The CTP build status is not important as we will switch to get
          # test result from RDB in the next CL. So just use the first build
          # here.
          build_id=int(ctp_builds.values()[0].id),
          status=ctp_builds.values()[0].status,
          responses=tagged_responses)

  def _enable_test_retries(self, req, retries):
    """Enable test retries within a single CTP build.

    Args:
      req: A request.Request object.
      retries: See structs.SkylabRequest.
    """
    req.params.retry.max = retries
    req.params.retry.allow = True

  def _get_skylab_task_result(self, execute_response):
    """Emit the skylab task, aka tast suite, result from a CTP response."""
    for c in execute_response.consolidated_results:
      for a in c.attempts:
        yield a

  def _get_multi_response_binary(self, build):
    """Get the tagged CTP response dict from a Buildbucket call."""
    try:
      resps = build.output.properties['compressed_responses']
    # Defer the exception later, because there may be still good results
    # from other CTP builds.
    # If the build object has no output field, it does not
    # matter what we return here. So no cover. Plus, the entire
    # CTP response related code will be removed by the following CL.
    except ValueError:  # pragma: no cover
      return ExecuteResponses().tagged_responses
    wire_format = resps.decode('base64_codec').decode('zlib_codec')
    responses = ExecuteResponses.FromString(wire_format)
    return responses.tagged_responses

  def _default_failed_response(self):
    """Generate a failed empty CTP response."""
    response = ExecuteResponse()
    response.state.verdict = TaskState.VERDICT_FAILED
    response.state.life_cycle = TaskState.LIFE_CYCLE_COMPLETED
    return response

  def _translate_result(self, execute_response):
    """Translates result to a list of SkylabResponse."""
    results = []
    for task in self._get_skylab_task_result(execute_response):
      # TODO(crbug/1145385): Use terzetto or result DB to fetch the test
      # result, instead of calculating it here.
      if task.state.verdict == TaskState.VERDICT_PASSED:
        status = common_pb2.SUCCESS
      elif task.state.life_cycle in (TaskState.LIFE_CYCLE_CANCELLED,
                                     TaskState.LIFE_CYCLE_PENDING,
                                     TaskState.LIFE_CYCLE_ABORTED,
                                     TaskState.LIFE_CYCLE_REJECTED):
        status = common_pb2.INFRA_FAILURE
      else:
        status = common_pb2.FAILURE
      results.append(
          structs.SkylabResponse.create(
              tast_suite=task.name,
              url=task.task_url,
              status=status,
              log_url=task.log_url,
              log_gs_uri=task.log_data.gs_url,
              verdict=self._unify_verdict(task.state.verdict),
              test_cases=self._get_test_cases(task.test_cases)))
    return results

  def _get_test_cases(self, test_cases):
    """Translate the test case result to SkylabTestCase."""
    cases = []
    for c in test_cases:
      cases.append(
          structs.SkylabTestCase.create(
              name=c.name, verdict=self._unify_verdict(c.verdict)))
    return cases

  def _unify_verdict(self, verdict):
    return "PASSED" if verdict == TaskState.VERDICT_PASSED else "FAILED"

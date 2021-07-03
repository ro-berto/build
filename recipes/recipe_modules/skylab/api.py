# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64

from google.protobuf import json_format

from recipe_engine import recipe_api

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

  def schedule_suites(self, name, requests, retry=False):
    """Schedule CrOS autotest suites by invoking the cros_test_platform recipe.

    Args:
    * name (str): The step name.
    * requests (list[SkylabRequest]): List of Autotest suites to schedule.
    * retry (bool): If True, retry at most 5 times within this invocation.

    Returns:
      ctp_build_id[str]: a cros_test_platform build ID.
    """

    name = name or 'schedule skylab tests'
    with self.m.step.nest(name) as presentation:
      # str -> (Request in jsonpb)
      reqs = {}

      for s in requests:
        req = Request()
        gs_img_uri = CROS_BUCKET + s.cros_img
        req.params.metadata.test_metadata_url = gs_img_uri
        req.params.metadata.debug_symbols_archive_url = gs_img_uri
        sw_dep = req.params.software_dependencies.add()
        sw_dep.chromeos_build = s.cros_img
        req.params.scheduling.managed_pool = POOL
        req.params.scheduling.qs_account = QS_ACCOUNT
        req.params.software_attributes.build_target.name = s.board
        req.params.time.maximum_duration.seconds = s.timeout_sec
        autotest_to_create = req.test_plan.test.add()
        autotest_name = AUTOTEST_NAME_CHROMIUM
        if s.test_type == structs.SKYLAB_TAST_TEST:
          autotest_name = AUTOTEST_NAME_TAST
        autotest_to_create.autotest.name = autotest_name
        tags = {
            'label-pool': 'DUT_POOL_QUOTA',
            'label-board': s.board,
            'build': gs_img_uri,
            'suite': autotest_name,
        }
        test_args = ['dummy=crbug.com/984103']
        if s.tast_expr:
          # Due to crbug/1173329, skylab does not support arbitrary tast
          # expressions. As a workaround, we encode test argument which may
          # contain complicated patterns to base64.
          test_args.append('tast_expr_b64=%s' % base64.b64encode(s.tast_expr))
          tags['tast-expr'] = s.tast_expr
        if s.test_args:
          test_args.append('test_args_b64=%s' % base64.b64encode(s.test_args))
          tags['test_args'] = s.test_args
        if s.lacros_gcs_path:
          lacros_dep = req.params.software_dependencies.add()
          lacros_dep.lacros_gcs_path = s.lacros_gcs_path
          test_args.append('lacros_gcs_path=%s' % s.lacros_gcs_path)
        if s.exe_rel_path:
          test_args.append('exe_rel_path=%s' % s.exe_rel_path)
          tags['exe_rel_path'] = s.exe_rel_path
        autotest_to_create.autotest.test_args = ' '.join(test_args)
        swarming_tags = [
            '{}:{}'.format(key, value) for key, value in tags.items()
        ]
        req.params.decorations.tags.extend(swarming_tags)
        if retry:
          self._enable_test_retries(req)
        reqs[s.request_tag] = json_format.MessageToDict(req)

      # We're sending this only to add a link back to the parent. This will not
      # cause cascading termination. For that see swarming_parent_run_id.
      bb_tags = {'parent_buildbucket_id': str(self.m.buildbucket.build.id)}
      bb_request = self.m.buildbucket.schedule_request(
          CTP_BUILDER_DEV if self.m.runtime.is_experimental else CTP_BUILDER,
          project='chromeos',
          bucket='testplatform',
          properties={
              'requests': reqs,
          },
          tags=self.m.buildbucket.tags(**bb_tags),
          gerrit_changes=[],
          exe_cipd_version='')
      build = self.m.buildbucket.schedule([bb_request])[0]
      build_url = self.m.buildbucket.build_url(build_id=build.id)
      presentation.links['suite link'] = build_url
      # Build.id is int64, implemented in recipe as long.
      # This is safe on a 64bit CPU bot for CTP build ID,
      # e.g. 8863223149660721536.
      return int(build.id)

  def wait_on_suites(self, ctp_build_id, timeout_seconds):
    """Wait for the CTP build to complete and return the result

    Args:
      ctp_build_id (int): The CTP build ID, which this function is waiting for.
      timeout_seconds (int): How long to wait for results before
        giving up.

    Returns:
      list[SkylabSuiteResponse]: The results for the provided requests.
    """
    if not ctp_build_id:
      return []
    with self.m.step.nest('collect skylab results') as presentation:
      try:
        ctp_build = self.m.buildbucket.collect_build(
            ctp_build_id, timeout=timeout_seconds)
      except recipe_api.StepFailure as ex:
        # 'collect skylab results' fails if we hit the deadline or something
        # unexpected happened inside collect_build(). As long as the CTP build
        # result is fetched, this step is green in spite of the build status.
        presentation.status = 'FAILURE' if ex.had_timeout else 'EXCEPTION'
        ctp_build = self.m.buildbucket.get(ctp_build_id)

      tagged_responses = {}
      responses = self._get_multi_response_binary(ctp_build)
      for t in responses:
        # Note, request tag is mapped to a list of responses, because CTP has
        # retry logic. A single request may have multiple attempts executed.
        tagged_responses[t] = self._translate_result(
            responses.get(t, self._default_failed_response()))

      presentation.logs['return value'] = [str(t) for t in tagged_responses]

      return structs.SkylabTaggedResponses.create(
          build_id=ctp_build_id,
          status=ctp_build.status,
          responses=tagged_responses)

  def _enable_test_retries(self, req):
    """Enable test retries within suites.

    Args:
      params: A request.Request object.
    """
    req.params.retry.max = 5
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
    except ValueError:
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

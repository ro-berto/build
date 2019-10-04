# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

from PB.go.chromium.org.luci.buildbucket.proto import common as common_pb2
from PB.recipe_engine import result as result_pb2

import json
import re

DEPS = [
  'chromite',
  'depot_tools/gitiles',
  'recipe_engine/properties',
]

_CHROMEOS_GOMA_CIPD_PLATFORM = 'chromeos-amd64'
_LINUX_GOMA_CIPD_PLATFORM = 'linux-amd64'


def RunSteps(api):
  result = result_pb2.RawResult(
      status = common_pb2.SUCCESS,
  )

  try:
    DoRunSteps(api)
  except recipe_api.InfraFailure as ex:  #pragma: no cover
    result.status = common_pb2.INFRA_FAILURE
    result.summary_markdown = MakeSummaryMarkdown(api, ex)
  except recipe_api.AggregatedStepFailure as ex:  #pragma: no cover
    if ex.result.contains_infra_failure:
      result.status = common_pb2.INFRA_FAILURE
    else:
      result.status = common_pb2.FAILURE
    result.summary_markdown = MakeSummaryMarkdown(api, ex)
  except recipe_api.StepFailure as ex:
    result.status = common_pb2.FAILURE
    result.summary_markdown = MakeSummaryMarkdown(api, ex)

  return result

def DoRunSteps(api):
  # Get parameters specified in the tryjob description.
  cbb_extra_args = api.properties.get('cbb_extra_args', [])

  # If cbb_extra_args is a non-empty string, translate from json to list.
  if cbb_extra_args and isinstance(cbb_extra_args, basestring):
    cbb_extra_args = json.loads(cbb_extra_args)

  # Apply our adjusted configuration.
  api.chromite.configure(
      api.properties,
      {},
      CBB_EXTRA_ARGS=cbb_extra_args)

  # Fetch chromite and pinned depot tools.
  api.chromite.checkout_chromite()

  # Update or install goma client via cipd.
  api.chromite.m.goma.ensure_goma(
      client_type = api.properties.get('cbb_goma_client_type'),
      additional_platforms=[
          _LINUX_GOMA_CIPD_PLATFORM,
          _CHROMEOS_GOMA_CIPD_PLATFORM],
      # TODO(crbug.com/997733): remove ephemeral when we find the way to
      #                         avoid use of GLIBC 2.27 in legacy bots.
      ephemeral=True)

  # Use the system python, not "bundled python" so that we have access
  # to system python packages.
  with api.chromite.with_system_python():
    api.chromite.run(
        goma_dir=api.chromite.m.goma.additional_goma_dir(
            _LINUX_GOMA_CIPD_PLATFORM))

def MakeSummaryMarkdown(api, failure):
  lines = []
  lines.append(failure.reason)

  cbb_config = api.properties.get('cbb_config', None)
  if cbb_config:
    lines.append('builder: %s' % cbb_config)

  buildset = api.properties.get('buildset', '')
  m = re.match('^cros/master_buildbucket_id/(\d+)$', buildset)
  if m:
    lines.append('[master](https://ci.chromium.org/b/%s)' % m.groups()[0])

  return '\n\n'.join(lines)

def GenTests(api):

  common_properties = {
      'buildername': 'Test',
      'bot_id': 'test_builder',
      'buildbucket': {
          'build': {
              'id': '12345'
          }
      },
  }

  # Test a minimal invocation.
  yield api.test(
      'swarming_builder',
      api.properties(
          bot_id='test',
          cbb_config='swarming-build-config',
      ),
  )

  # Tests the summary_markdown generation, only works on failure for now
  yield api.test(
      'swarming_builder_fails',
      api.properties(
          bot_id='test',
          cbb_config='swarming-build-config',
          buildset='cros/master_buildbucket_id/8904538489270332096',
      ),
      api.step_data('cbuildbot_launch [swarming-build-config]', retcode=1),
  )

  # Test a plain tryjob.
  yield api.test(
      'tryjob_simple',
      api.properties(
          cbb_config='tryjob_config',
          cbb_extra_args='["--remote-trybot"]',
          email='user@google.com',
          **common_properties),
  )

  # Test a tryjob with a branch and CLs.
  yield api.test(
      'tryjob_complex',
      api.properties(
          cbb_config='tryjob_config',
          cbb_extra_args='["--remote-trybot", "-b", "release-R65-10323.B",'
          ' "-g", "900169", "-g", "902706"]',
          email='user@google.com',
          **common_properties),
  )

  # Test a tryjob with a branch and CLs.
  yield api.test(
      'master_builder',
      api.properties(
          branch='',
          cbb_branch='slave_branch',
          cbb_config='master_config',
          **common_properties),
  )

  # Test a tryjob with a branch and CLs.
  yield api.test(
      'complex_slave_builder',
      api.properties(
          branch='',
          cbb_branch='slave_branch',
          cbb_config='slave_config',
          cbb_master_build_id=123,
          **common_properties),
  )

  # Test empty string args.
  yield api.test(
      'empty_string_args',
      api.properties(
          cbb_config='tryjob_config',
          cbb_extra_args='',
          email='user@google.com',
          **common_properties),
  )

  # Test tuple args. I'm not sure what mechanism gets them here, but it
  # can happen.
  yield api.test(
      'tuple_args',
      api.properties(
          cbb_config='tryjob_config',
          cbb_extra_args=('--remote-trybot', '-foo'),
          email='user@google.com',
          **common_properties),
  )

  yield api.test(
      'goma_canary',
      api.properties(
          cbb_config='amd64-generic-goma-canary-chromium-pfq-informational',
          cbb_goma_canary=True,
          email='user@google.com',
          **common_properties),
  )

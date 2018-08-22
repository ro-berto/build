# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

DEPS = [
  'chromite',
  'depot_tools/gitiles',
  'recipe_engine/properties',
]


def RunSteps(api):
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
  # TODO(yyanagisawa): use cbb_goma_client_type instead (crbug.com/876585)
  client_type = None
  if api.properties.get('cbb_goma_canary', False):
    client_type = 'candidate'
  api.chromite.m.goma.ensure_goma(client_type=client_type)

  # Use the system python, not "bundled python" so that we have access
  # to system python packages.
  with api.chromite.with_system_python():
    api.chromite.run()


def GenTests(api):

  common_properties = {
    'buildername': 'Test',
    'bot_id': 'test_builder',
    'buildbucket': {'build': {'id':'12345'}},
  }

  # Test a minimal invocation.
  yield (
      api.test('swarming_builder')
      + api.properties(
          bot_id='test',
          cbb_config='swarming-build-config',
      )
  )

  # Test a plain tryjob.
  yield (
      api.test('tryjob_simple')
      + api.properties(
          cbb_config='tryjob_config',
          cbb_extra_args='["--remote-trybot"]',
          email='user@google.com',
          **common_properties
      )
  )

  # Test a tryjob with a branch and CLs.
  yield (
      api.test('tryjob_complex')
      + api.properties(
          cbb_config='tryjob_config',
          cbb_extra_args='["--remote-trybot", "-b", "release-R65-10323.B",'
                         ' "-g", "900169", "-g", "902706"]',
          email='user@google.com',
          **common_properties
      )
  )

  # Test a tryjob with a branch and CLs.
  yield (
      api.test('master_builder')
      + api.properties(
          branch='',
          cbb_branch='slave_branch',
          cbb_config='master_config',
          **common_properties
      )
  )

  # Test a tryjob with a branch and CLs.
  yield (
      api.test('complex_slave_builder')
      + api.properties(
          branch='',
          cbb_branch='slave_branch',
          cbb_config='slave_config',
          cbb_master_build_id=123,
          **common_properties
      )
  )

  # Test empty string args.
  yield (
      api.test('empty_string_args')
      + api.properties(
          cbb_config='tryjob_config',
          cbb_extra_args='',
          email='user@google.com',
          **common_properties
      )
  )

  # Test tuple args. I'm not sure what mechanism gets them here, but it
  # can happen.
  yield (
      api.test('tuple_args')
      + api.properties(
          cbb_config='tryjob_config',
          cbb_extra_args=('--remote-trybot', '-foo'),
          email='user@google.com',
          **common_properties
      )
  )

  yield (
      api.test('goma_canary')
      + api.properties(
          cbb_config='amd64-generic-goma-canary-chromium-pfq-informational',
          cbb_goma_canary=True,
          email='user@google.com',
          **common_properties
      )
  )

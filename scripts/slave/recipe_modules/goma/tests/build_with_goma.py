# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'goma',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
]


def RunSteps(api):
  api.goma.ensure_goma()
  api.goma.build_with_goma(
      ['ninja', '-C', api.path['checkout'].join('out', 'Release')])

  api.step('jsonstatus', [])
  api.step.active_result.presentation.logs['details'] = [
      'jsonstatus: %r' % api.goma.jsonstatus,
  ]


def GenTests(api):
  yield api.test(
      'basic',
      api.properties(buildername='test_buildername'),
  )
  yield api.test(
      'enable_ats',
      api.properties(buildername='test_buildername'),
      api.goma(enable_ats=True),
  )
  yield api.test(
      'server_host',
      api.properties(buildername='test_buildername'),
      api.goma(server_host="goma.chromium.org", rpc_extra_params="?prod"),
  )

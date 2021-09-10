# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

PYTHON_VERSION_COMPATIBILITY = "PY2"

DEPS = [
    'goma',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/properties',
    'recipe_engine/step',
]


def RunSteps(api):
  api.goma.ensure_goma()
  api.goma.build_with_goma(
      ['ninja', '-C', api.path['checkout'].join('out', 'Release')],
      goma_env=api.m.properties.get('env'),
  )

  api.step('jsonstatus', [])
  api.step.active_result.presentation.logs['details'] = [
      'jsonstatus: %r' % api.goma.jsonstatus,
  ]


def GenTests(api):
  yield api.test(
      'basic',
      api.buildbucket.ci_build(),
  )
  yield api.test(
      'enable_ats',
      api.goma(enable_ats=True),
      api.buildbucket.ci_build(),
  )
  yield api.test(
      'server_host',
      api.goma(server_host="goma.chromium.org", rpc_extra_params="?prod"),
      api.buildbucket.ci_build(),
  )
  yield api.test(
      'large_cache_file',
      api.properties(env={'GOMA_DEPS_CACHE_MAX_PROTO_SIZE_IN_MB': 256}),
      api.buildbucket.ci_build(),
  )

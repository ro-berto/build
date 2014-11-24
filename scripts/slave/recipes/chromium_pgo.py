# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'pgo',
  'platform',
  'properties',
  'step',
]


PGO_BUILDERS = {
  'chromium.fyi': {
    'Chromium Win PGO Builder': {
      'chromium_config_instrument': 'chromium_pgo_instrument',
      'chromium_config_optimize': 'chromium_pgo_optimize',
      'gclient_config': 'chromium_lkgr',
      'chromium_config_kwargs': {
        'BUILD_CONFIG': 'Release',
        'TARGET_BITS': 32,
      },
    },
  },
}


def GenSteps(api):
  api.chromium.add_builders(PGO_BUILDERS)
  api.pgo.compile_pgo()


def GenTests(api):
  mastername = 'chromium.fyi'
  buildername = 'Chromium Win PGO Builder'

  def _sanitize_nonalpha(text):
    return ''.join(c if c.isalnum() else '_' for c in text)

  yield (
    api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                             _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername, buildername=buildername) +
    api.platform('win', 32)
  )

  yield (
    api.test('full_%s_%s_benchmark_failure' %
        (_sanitize_nonalpha(mastername), _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername, buildername=buildername) +
    api.platform('win', 32) +
    api.step_data('Telemetry benchmark: peacekeeper.dom', retcode=1)
  )

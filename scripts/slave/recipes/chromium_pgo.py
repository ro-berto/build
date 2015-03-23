# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'archive',
  'chromium',
  'pgo',
  'platform',
  'properties',
  'step',
]


def GenSteps(api):
  api.pgo.compile_pgo()
  api.archive.zip_and_upload_build(
      'package build',
      api.chromium.c.build_config_fs,
      'gs://chromium-fyi-archive/win_pgo_builds')


def GenTests(api):
  pgo_builders = {
    'chromium.fyi': ['Chromium Win PGO Builder'],
    'tryserver.chromium.win': ['win_pgo'],
  }

  def _sanitize_nonalpha(text):
    return ''.join(c if c.isalnum() else '_' for c in text)

  for mastername, builders in pgo_builders.iteritems():
    for buildername in builders:
      yield (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(mastername=mastername, buildername=buildername) +
        api.platform('win', 32)
      )

  yield (
    api.test('full_%s_%s_benchmark_failure' %
        (_sanitize_nonalpha('chromium.fyi'),
         _sanitize_nonalpha('Chromium Win PGO Builder'))) +
    api.properties.generic(mastername='chromium.fyi',
                           buildername='Chromium Win PGO Builder') +
    api.platform('win', 32) +
    api.step_data('Telemetry benchmark: sunspider', retcode=1)
  )

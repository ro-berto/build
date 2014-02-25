# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'step',
  'tryserver',
  'webrtc',
]


def GenSteps(api):
  config_vals = {}
  config_vals.update(
    dict((str(k),v) for k,v in api.properties.iteritems() if k.isupper())
  )
  api.webrtc.set_config('webrtc_standalone', **config_vals)
  api.step.auto_resolve_conflicts = True

  yield api.gclient.checkout()
  yield api.chromium.runhooks()
  if api.tryserver.is_tryserver:
    yield api.webrtc.apply_svn_patch()

  yield api.chromium.compile()
  yield api.webrtc.add_baremetal_tests()


def GenTests(api):
  for plat in ('win', 'mac', 'linux'):
    for bits in (32, 64):
      for build_config in ('Debug', 'Release'):
        yield (
          api.test('buildbot_%s%s_%s' % (plat, bits, build_config)) +
          api.properties(BUILD_CONFIG=build_config,
                         TARGET_BITS=bits,
                         buildername='buildbot builder',
                         slavename='slavename',
                         mastername='mastername') +
          api.platform(plat, bits)
        )

  for plat in ('win', 'mac', 'linux'):
    for bits in (32, 64):
      for build_config in ('Debug', 'Release'):
        yield (
          api.test('trybot_%s%s_%s' % (plat, bits, build_config)) +
          api.properties(BUILD_CONFIG=build_config,
                         TARGET_BITS=bits,
                         buildername='trybot builder',
                         slavename='slavename',
                         mastername='mastername',
                         revision='12345',
                         patch_url='try_job_svn_patch') +
          api.platform(plat, bits)
        )

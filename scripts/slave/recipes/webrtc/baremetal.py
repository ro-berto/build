# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'platform',
  'properties',
  'tryserver',
  'webrtc',
]


def GenSteps(api):
  config_vals = {}
  config_vals.update(
    dict((str(k),v) for k,v in api.properties.iteritems() if k.isupper())
  )
  api.webrtc.set_config('webrtc_standalone', **config_vals)

  yield api.gclient.checkout()
  yield api.chromium.runhooks()
  if api.tryserver.is_tryserver:
    yield api.webrtc.apply_svn_patch()

  yield api.chromium.compile()
  yield api.webrtc.add_baremetal_tests()


def GenTests(api):

  def props(build_config, bits, buildername, revision=None, patch_url=None):
    return api.properties(BUILD_CONFIG=build_config,
                         TARGET_BITS=bits,
                         buildername=buildername,
                         slavename='slavename',
                         mastername='mastername',
                         revision=revision,
                         patch_url=patch_url)

  for kind in ['buildbot', 'trybot']:
    revision = '12345' if kind == 'trybot' else None
    patch_url = 'try_job_svn_patch' if kind == 'trybot' else None

    yield (
      api.test('%s_win32_Release' % kind) +
      props('Release', 32, kind, revision=revision, patch_url=patch_url) +
      api.platform('win', 64)
    )
    yield (
      api.test('%s_mac32_Release' % kind) +
      props('Release', 32, kind, revision=revision, patch_url=patch_url) +
      api.platform('mac', 64)
    )
    yield (
      api.test('%s_linux64_Release' % kind) +
      props('Release', 64, kind, revision=revision, patch_url=patch_url) +
      api.platform('linux', 64)
    )

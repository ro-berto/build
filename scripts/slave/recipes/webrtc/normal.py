# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Recipe for building and running the suite of tests that runs properly on a
# virtual machine (i.e. they don't rely on physical audio and/or video devices).

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
  if api.tryserver.is_tryserver:
    api.chromium.apply_config('trybot_flavor')

  yield api.gclient.checkout()
  yield api.chromium.runhooks()
  if api.tryserver.is_tryserver:
    yield api.webrtc.apply_svn_patch()

  yield api.chromium.compile()
  yield api.webrtc.add_normal_tests()


def GenTests(api):

  def props(build_config, bits, buildername, target_platform=None,
            revision=None, patch_url=None):
    return api.properties(BUILD_CONFIG=build_config,
                          TARGET_BITS=bits,
                          buildername=buildername,
                          slavename='slavename',
                          mastername='mastername',
                          revision=revision,
                          patch_url=patch_url)

  for kind in ('buildbot', 'trybot'):
    revision = '12345' if kind == 'trybot' else None
    patch_url = 'try_job_svn_patch' if kind == 'trybot' else None

    for plat in ('win', 'mac', 'linux'):
      for bits in (32, 64):
        for build_config in ('Debug', 'Release'):
          yield (
            api.test('%s_%s%s_%s' % (kind, plat, bits, build_config)) +
            props(build_config, bits, kind, revision=revision,
                  patch_url=patch_url) +
            api.platform(plat, bits)
          )

    yield (
      api.test('%s_chromeos64_Release' % kind) +
      props('Release', 64, kind, revision=revision, patch_url=patch_url) +
      api.properties(TARGET_PLATFORM='chromeos') +
      api.platform('linux', 64)
    )

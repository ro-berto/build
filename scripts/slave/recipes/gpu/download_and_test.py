# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This recipe is intended to control all of the GPU testers on the
# following waterfalls:
#   chromium.gpu
#   chromium.gpu.fyi
#   chromium.webkit
# These testers are triggered by the builders on the same waterfall.

DEPS = [
  'gpu',
  'platform',
  'properties',
]

def GenSteps(api):
  api.gpu.setup()

  # Even the testers need a complete workspace:
  #  - runtest.py needs it in order to pick up the revision for the
  #    flakiness dashboard
  #  - the pixel tests need it in order to assign reasonable revisions
  #    to any error images (in particular, on bots on the Blink
  #    waterfall, which don't have a good revision coming in all the
  #    time from the buildbot master)
  yield api.gpu.checkout_steps()
  yield api.gpu.download_steps()
  yield api.gpu.test_steps()

def GenTests(api):
  # The majority of the tests are in the build_and_test recipe.

  # Keep the additional properties in sync with the build_and_upload
  # recipe in order to catch regressions.
  for plat in ['win', 'mac', 'linux']:
    yield (
      api.test('%s_release' % plat) +
      api.properties.scheduled(
        build_config='Release',
        mastername='chromium.gpu.testing',
        buildername='%s tester' % plat,
        buildnumber=776,
        parent_buildername='%s builder' % plat,
        parent_buildnumber=571) +
      api.platform.name(plat)
    )

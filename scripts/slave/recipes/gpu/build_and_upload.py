# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This recipe is intended to control all of the GPU builders on the
# following waterfalls:
#   chromium.gpu
#   chromium.gpu.fyi
#   chromium.webkit

DEPS = [
  'gpu',
  'platform',
  'properties',
]

def GenSteps(api):
  api.gpu.setup()
  yield api.gpu.checkout_steps()
  yield api.gpu.compile_steps()
  yield api.gpu.upload_steps()

def GenTests(api):
  # The majority of the tests are in the build_and_test recipe.

  # Keep the additional properties in sync with the download_and_test
  # recipe in order to catch regressions.
  for plat in ['win', 'mac', 'linux']:
    yield (
      api.test('%s_release' % plat) +
      api.properties.scheduled(
        build_config='Release',
        mastername='chromium.gpu.testing',
        buildername='%s builder' % plat,
        buildnumber=571) +
      api.platform.name(plat)
    )

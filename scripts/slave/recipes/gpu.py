# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This recipe is intended to control all of the GPU related bots:
#   chromium.gpu
#   chromium.gpu.fyi
#   The GPU bots on the chromium.webkit waterfall
#   The GPU bots on the tryserver.chromium waterfall

DEPS = [
  'gpu',
  'platform',
  'properties',
]

def GenSteps(api):
  api.gpu.setup()
  yield api.gpu.checkout_steps()
  yield api.gpu.compile_steps()
  yield api.gpu.test_steps()

def GenTests(api):
  for build_config in ['Release', 'Debug']:
    for plat in ['win', 'mac', 'linux']:
      # Normal builder configuration
      base_name = '%s_%s' % (plat, build_config.lower())
      yield (
        api.test(base_name) +
        api.properties.scheduled(build_config=build_config) +
        api.platform.name(plat)
      )

      # Blink builder configuration
      yield (
        api.test('%s_blink' % base_name) +
        api.properties.scheduled(
            build_config=build_config,
            top_of_tree_blink=True,
            project='webkit'
        ) +
        api.platform.name(plat)
      )

      # Try server configuration
      yield (
        api.test('%s_tryserver' % base_name) +
        api.properties.tryserver(build_config=build_config) +
        api.platform.name(plat)
      )

  # Test one configuration using git mode.
  yield (
    api.test('mac_release_git') +
    api.properties.git_scheduled(build_config='Release', use_git=True) +
    api.platform.name('mac')
  )

  # Test one trybot configuration with Blink issues.
  yield (
    api.test('mac_release_tryserver_blink') +
    api.properties.tryserver(
        build_config='Release',
        root='src/third_party/WebKit') +
    api.platform.name('mac')
  )

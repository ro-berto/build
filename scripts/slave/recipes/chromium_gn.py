# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'platform',
  'properties',
]


def GenSteps(api):
  # TODO: crbug.com/358481 . The build_config should probably be a property
  # passed in from slaves.cfg, but that doesn't exist today, so we need a
  # lookup mechanism to map bot name to build_config.
  build_config = {
    'Linux GN (dbg)': 'Debug',
  }[api.properties.get('buildername')]

  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium', BUILD_CONFIG=build_config)

  yield api.gclient.checkout(revert=True)

  yield api.chromium.runhooks(run_gyp=False)

  yield api.chromium.run_gn('//out/' + build_config)

  yield api.chromium.compile_with_ninja('compile', api.chromium.output_dir)

  # TODO(dpranke): crbug.com/353854. Run gn_unittests and other tests
  # when they are also being run as part of the try jobs.


def GenTests(api):
  yield (
      api.test('unittest_success') +
      api.properties.generic(buildername='Linux GN (dbg)') +
      api.platform.name('linux')
  )

  # TODO: crbug.com/354674. Figure out where to put "simulation"
  # tests. We should have one test for each bot this recipe runs on.
  yield (
      api.test('full_chromium_linux_Linux_GN__dbg_') +
      api.properties.generic(buildername='Linux GN (dbg)') +
      api.platform.name('linux')
  )

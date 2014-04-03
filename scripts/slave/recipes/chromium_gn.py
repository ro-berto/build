# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'step',
  'step_history',
  'tryserver',
]


def GenSteps(api):
  # TODO: crbug.com/358481 . The build_config should probably be a property
  # passed in from slaves.cfg, but that doesn't exist today, so we need a
  # lookup mechanism to map bot name to build_config.
  build_config = {
    'Linux GN (dbg)': 'Debug',
    'linux_chromium_gn': 'Debug',
  }[api.properties.get('buildername')]

  is_tryserver = api.tryserver.is_tryserver

  api.gclient.set_config('chromium')
  api.chromium.set_config('chromium', BUILD_CONFIG=build_config)
  api.step.auto_resolve_conflicts = True

  yield api.gclient.checkout(revert=True,
                             abort_on_failure=False,
                             can_fail_build=False)

  if is_tryserver:
    # maybe_apply_issue should work fine even w/o a patch, but this
    # is a little more explicit.
    yield api.tryserver.maybe_apply_issue()
    yield api.chromium.runhooks(run_gyp=False,
                                abort_on_failure=False,
                                can_fail_build=False)

    if any(step.retcode != 0 for step in api.step_history.values()):
      # Nuke the whole slave checkout and try again.
      yield api.path.rmcontents('slave build directory',
                                api.path['slave_build'])
      yield api.gclient.checkout(revert=False,
                                 abort_on_failure=True,
                                 can_fail_build=True)
      yield api.tryserver.maybe_apply_issue()
      yield api.chromium.runhooks(run_gyp=False,
                                  abort_on_failure=True,
                                  can_fail_build=True)
  else:
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

  yield (
      api.test('unittest_sync_fails') +
      api.properties.tryserver(buildername='linux_chromium_gn') +
      api.platform.name('linux') +
      api.step_data('gclient revert', retcode=1)
  )

  # This test should abort before running GN and trying to compile.
  yield (
      api.test('unittest_second_sync_fails') +
      api.properties.tryserver(buildername='linux_chromium_gn') +
      api.platform.name('linux') +
      api.step_data('gclient revert', retcode=1) +
      api.step_data('gclient sync (2)', retcode=1)
  )

  # TODO: crbug.com/354674. Figure out where to put "simulation"
  # tests. We should have one test for each bot this recipe runs on.
  yield (
      api.test('full_linux_chromium_gn') +
      api.properties.tryserver(buildername='linux_chromium_gn') +
      api.platform.name('linux')
  )

  yield (
      api.test('full_chromium_linux_Linux_GN__dbg_') +
      api.properties.generic(buildername='Linux GN (dbg)') +
      api.platform.name('linux')
  )

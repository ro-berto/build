# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia Swarming compile.


DEPS = [
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'skia',
]


TEST_BUILDERS = {
  'client.skia.compile': {
    'skiabot-linux-compile-000': [
      'Build-Mac-Clang-Arm7-Release-iOS',
      'Build-Ubuntu-GCC-Arm7-Debug-Android-Trybot',
      'Build-Ubuntu-GCC-Arm7-Release-Android',
      'Build-Ubuntu-GCC-Arm7-Release-Android_Vulkan',
      'Build-Ubuntu-GCC-x86_64-Release-PDFium',
    ],
    'skiabot-win-compile-000': [
      'Build-Win-MSVC-x86-Debug',
    ],
    'skiabot-linux-swarm-007': [
      'Build-Ubuntu-GCC-x86_64-Debug-MSAN',
    ],
    'skiabot-linux-swarm-012': [
      'Build-Ubuntu-GCC-x86_64-Release-Valgrind',
    ],
    'skiabot-linux-swarm-014': [
      'Build-Ubuntu-GCC-x86_64-Release-CMake',
    ],
    'skiabot-linux-swarm-015': [
      'Build-Mac-Clang-x86_64-Release-CMake',
    ],
  },
}


def RunSteps(api):
  api.skia.setup(running_in_swarming=True)
  api.skia.compile_steps()
  api.skia.cleanup_steps()
  api.skia.check_failure()


def GenTests(api):
  for mastername, slaves in TEST_BUILDERS.iteritems():
    for slavename, builders_by_slave in slaves.iteritems():
      for builder in builders_by_slave:
        test = (
          api.test(builder) +
          api.properties(buildername=builder,
                         mastername=mastername,
                         slavename=slavename,
                         buildnumber=5,
                         revision='abc123',
                         swarm_out_dir='[SWARM_OUT_DIR]') +
          api.path.exists(
              api.path['slave_build'].join('skia'),
              api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt'),
              api.path['slave_build'].join('.gclient_entries'),
          )
        )
        if 'Win' in builder:
          test += api.platform('win', 64)

        if 'Android' in builder:
          ccache = '/usr/bin/ccache' if 'Appurify' in builder else None
          test += api.step_data('has ccache?',
                                stdout=api.json.output({'ccache':ccache}))
          test += api.step_data(
            'which adb',
            retcode=1)
        if 'Trybot' in builder:
          test += api.properties(issue=500,
                                 patchset=1,
                                 rietveld='https://codereview.chromium.org')

        yield test

  mastername = 'client.skia.compile'
  slavename = 'skiabot-win-compile-000'
  buildername = 'Build-Win-MSVC-x86-Debug'
  yield (
      api.test('win_cleanup_after_failed_compile') +
      api.properties(buildername=buildername,
                     mastername=mastername,
                     slavename=slavename,
                     buildnumber=5,
                     revision='abc123',
                     swarm_out_dir='[SWARM_OUT_DIR]') +
      api.path.exists(
          api.path['slave_build'].join('skia'),
          api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
      ) +
      api.platform('win', 64) +
      api.step_data('build most', retcode=1)
  )

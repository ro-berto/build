# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia builders.


DEPS = [
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
  'skia',
]


TEST_BUILDERS = {
  'client.skia': {
    'build20-m3': [
      'Test-Mac-Clang-MacMini6.2-GPU-HD4000-x86_64-Debug-CommandBuffer',
    ],
    'skiabot-ipad4-000': [
      'Test-iOS-Clang-iPad4-GPU-SGX554-Arm7-Debug',
    ],
    'skiabot-linux-tester-000': [
      'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug',
      'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Release-TSAN',
    ],
    'skiabot-shuttle-ubuntu12-gtx550ti-001': [
      'Perf-Ubuntu-GCC-ShuttleA-GPU-GTX550Ti-x86_64-Release-VisualBench',
    ],
    'skiabot-shuttle-win8-i7-4790k-001': [
      'Perf-Win8-MSVC-ShuttleB-GPU-HD4600-x86_64-Release-Trybot',
    ],
  },
  'client.skia.android': {
    'skiabot-shuttle-ubuntu12-nexus7-001': [
      'Perf-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Release',
      'Test-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Debug',
    ],
  },
  'client.skia.compile': {
    'skiabot-mac-10_8-compile-001': [
      'Build-Mac10.8-Clang-Arm7-Debug-Android',
    ],
    'vm692-m3': [
      'Build-Mac10.9-Clang-Arm7-Debug-iOS',
    ],
    'skiabot-linux-compile-000': [
      'Build-Ubuntu-GCC-Arm7-Debug-Android',
      'Build-Ubuntu-GCC-x86_64-Release-CMake',
    ],
    'skiabot-win-compile-000': [
      'Build-Win-MSVC-x86-Debug',
    ],
  },
  'client.skia.fyi': {
    'skiabot-linux-housekeeper-003': [
      'Housekeeper-PerCommit',
      'Housekeeper-PerCommit-Trybot',
      'Perf-Android-GCC-Nexus5-CPU-NEON-Arm7-Release-Appurify',
      'Perf-Android-GCC-Nexus5-GPU-Adreno330-Arm7-Release-Appurify',
    ],
  },
}


def RunSteps(api):
  api.skia.gen_steps()


def GenTests(api):
  def AndroidTestData(builder, adb=None):
    test_data = (
        api.step_data(
            'get EXTERNAL_STORAGE dir',
            stdout=api.raw_io.output('/storage/emulated/legacy')) +
        api.step_data(
            'read SKP_VERSION',
            stdout=api.raw_io.output('42')) +
        api.step_data(
            'read SK_IMAGE_VERSION',
            stdout=api.raw_io.output('42'))
    )
    if adb:
      test_data += api.step_data(
          'which adb',
          stdout=api.raw_io.output(adb))
    else:
      test_data += api.step_data(
        'which adb',
        retcode=1)
    if 'Test' in builder:
      test_data += (
        api.step_data(
            'exists skia_dm',
            stdout=api.raw_io.output(''))
      )

    if 'Perf' in builder:
      test_data += api.step_data(
          'exists skia_perf',
          stdout=api.raw_io.output(''))
    return test_data

  for mastername, slaves in TEST_BUILDERS.iteritems():
    for slavename, builders_by_slave in slaves.iteritems():
      for builder in builders_by_slave:
        test = (
          api.test(builder) +
          api.properties(buildername=builder,
                         mastername=mastername,
                         slavename=slavename,
                         buildnumber=5,
                         revision='abc123') +
          api.path.exists(
              api.path['slave_build'].join('skia'),
              api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
          )
        )
        if 'Android' in builder:
          ccache = '/usr/bin/ccache' if 'Appurify' in builder else None
          test += api.step_data('has ccache?',
                                stdout=api.json.output({'ccache':ccache}))
        if 'Android' in builder and not 'Appurify' in builder:
          if 'Test' in builder or 'Perf' in builder:
            test += AndroidTestData(builder)
          else:
            test += api.step_data(
                'which adb',
                retcode=1)
        if 'Trybot' in builder:
          test += api.properties(issue=500,
                                 patchset=1,
                                 rietveld='https://codereview.chromium.org')
        if 'Win' in builder and 'Swarming' not in builder:
          test += api.platform('win', 64)
          test += api.path.exists(
              api.path['slave_build'].join('skia', 'infra', 'bots',
                                           'win_toolchain_hash.json'))
          test += api.step_data('Get downloaded WIN_TOOLCHAIN_HASH',
                                retcode=1)

        yield test

  builder = 'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug'
  yield (
    api.test('failed_dm') +
    api.properties(buildername=builder,
                   mastername='client.skia',
                   slavename='skiabot-linux-tester-000',
                   buildnumber=6) +
    api.step_data('dm', retcode=1) +
    api.path.exists(api.path['slave_build'])
  )

  yield (
    api.test('has_ccache_android') +
    api.properties(buildername='Build-Ubuntu-GCC-Arm7-Debug-Android',
                   mastername='client.skia.compile',
                   slavename='skiabot-linux-compile-000') +
    api.step_data(
                'has ccache?',
                stdout=api.json.output({'ccache':'/usr/bin/ccache'})) +
    api.path.exists(api.path['slave_build']) +
    api.step_data(
        'which adb',
        retcode=1)
  )

  builder = 'Test-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Debug'
  master = 'client.skia.android'
  slave = 'skiabot-shuttle-ubuntu12-nexus7-001'
  yield (
    api.test('failed_get_hashes') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data(
                'has ccache?',
                stdout=api.json.output({'ccache':None})) +
    AndroidTestData(builder) +
    api.step_data('read SKP_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.step_data('read SK_IMAGE_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.step_data('get uninteresting hashes', retcode=1) +
    api.path.exists(
        api.path['slave_build'].join('skia'),
        api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
    )
  )

  yield (
    api.test('download_and_push_skps') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123',
                   test_downloaded_skp_version='2') +
    api.step_data(
                'has ccache?',
                stdout=api.json.output({'ccache':None})) +
    AndroidTestData(builder) +
    api.step_data('read SKP_VERSION',
                  stdout=api.raw_io.output('2')) +
    api.step_data('read SK_IMAGE_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.step_data(
        'exists skps',
        stdout=api.raw_io.output('')) +
    api.path.exists(
        api.path['slave_build'].join('skia'),
        api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
    )
  )

  yield (
    api.test('missing_SKP_VERSION_device') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data(
                'has ccache?',
                stdout=api.json.output({'ccache':None})) +
    AndroidTestData(builder) +
    api.step_data('read SKP_VERSION',
                  retcode=1) +
    api.step_data('read SK_IMAGE_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.step_data(
        'exists skps',
        stdout=api.raw_io.output('')) +
    api.path.exists(
        api.path['slave_build'].join('skia'),
        api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
    )
  )

  yield (
    api.test('download_and_push_skimage') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123',
                   test_downloaded_sk_image_version='2') +
    api.step_data(
                'has ccache?',
                stdout=api.json.output({'ccache':None})) +
    AndroidTestData(builder) +
    api.step_data('read SKP_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.step_data('read SK_IMAGE_VERSION',
                  stdout=api.raw_io.output('2')) +
    api.step_data(
        'exists skia_images',
        stdout=api.raw_io.output('')) +
    api.path.exists(
        api.path['slave_build'].join('skia'),
        api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
    )
  )

  yield (
    api.test('missing_SK_IMAGE_VERSION_device') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data(
                'has ccache?',
                stdout=api.json.output({'ccache':None})) +
    AndroidTestData(builder) +
    api.step_data('read SKP_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.step_data('read SK_IMAGE_VERSION',
                  retcode=1) +
    api.step_data(
        'exists skia_images',
        stdout=api.raw_io.output('')) +
    api.path.exists(
        api.path['slave_build'].join('skia'),
        api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
    )
  )

  builder = 'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug'
  master = 'client.skia'
  slave = 'skiabot-linux-test-000'
  yield (
    api.test('missing_SKP_VERSION_host') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data('Get downloaded SKP_VERSION', retcode=1) +
    api.path.exists(
        api.path['slave_build'].join('skia'),
        api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
    )
  )

  yield (
    api.test('missing_SK_IMAGE_VERSION_host') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data('Get downloaded SK_IMAGE_VERSION', retcode=1) +
    api.path.exists(
        api.path['slave_build'].join('skia'),
        api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
    )
  )

  builder = 'Test-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Debug'
  slave = 'skiabot-shuttle-ubuntu12-nexus7-001'
  master = 'client.skia.android'
  yield (
    api.test('adb_in_path') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data(
                'has ccache?',
                stdout=api.json.output({'ccache':None})) +
    AndroidTestData(builder, adb='/usr/bin/adb') +
    api.step_data('read SKP_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.step_data('read SK_IMAGE_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.path.exists(
        api.path['slave_build'].join('skia'),
        api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
    )
  )


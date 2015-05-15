# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia builders.


from common.skia import builder_name_schema


DEPS = [
  'json',
  'path',
  'platform',
  'properties',
  'raw_io',
  'skia',
]


def GenSteps(api):
  api.skia.gen_steps()


def GenTests(api):
  builders = {
    'client.skia': {
      'skiabot-ipad4-000': [
        'Test-iOS-Clang-iPad4-GPU-SGX554-Arm7-Debug',
      ],
      'skiabot-linux-tester-000': [
        'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Release-Shared',
        'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Release-TSAN',
      ],
      'skiabot-macmini-10_8-000': [
        'Test-Mac10.8-Clang-MacMini4.1-GPU-GeForce320M-x86_64-Release',
      ],
      'skiabot-shuttle-ubuntu12-003': [
        'Test-ChromeOS-GCC-Link-CPU-AVX-x86_64-Debug',
      ],
      'skiabot-shuttle-ubuntu12-gtx550ti-001': [
        'Test-Ubuntu-GCC-ShuttleA-GPU-GTX550Ti-x86_64-Release-Valgrind',
        'Test-Ubuntu-GCC-ShuttleA-GPU-GTX550Ti-x86_64-Debug-ZeroGPUCache',
      ],
      'skiabot-shuttle-win7-intel-000': [
        'Test-Win7-MSVC-ShuttleA-GPU-HD2000-x86-Release-ANGLE',
      ],
      'skiabot-shuttle-win7-intel-bench': [
        'Perf-Win7-MSVC-ShuttleA-GPU-HD2000-x86_64-Release-Trybot',
      ],
      'skiabot-shuttle-win8-hd7770-000': [
        'Test-Win8-MSVC-ShuttleA-CPU-AVX-x86_64-Debug',
      ],
    },
    'client.skia.android': {
      'skiabot-shuttle-ubuntu12-nexus7-001': [
        'Perf-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Release',
      ],
    },
    'client.skia.compile': {
      'skiabot-linux-compile-000': [
        'Build-Ubuntu-GCC-Arm7-Debug-CrOS_Daisy',
        'Build-Ubuntu-GCC-Arm7-Debug-CrOS_Link',
        'Build-Ubuntu-GCC-x86_64-Release-Mesa',
        'Build-Ubuntu-GCC-Arm7-Debug-Android_NoNeon',
      ],
      'skiabot-mac-10_8-compile-001': [
        'Build-Mac10.8-Clang-Arm7-Debug-Android',
      ],
      'skiabot-win-compile-000': [
        'Build-Win-MSVC-x86-Debug',
        'Build-Win-MSVC-x86-Debug-GDI',
        'Build-Win-MSVC-x86-Debug-Exceptions',
      ],
    },
  }

  def AndroidTestData(builder):
    test_data = (
        api.step_data(
            'get EXTERNAL_STORAGE dir',
            stdout=api.raw_io.output('/storage/emulated/legacy')) +
        api.step_data(
            'read SKP_VERSION',
            stdout=api.raw_io.output('42'))
    )
    if 'Test' in builder:
      test_data += (
        api.step_data(
            'exists skia_dm',
            stdout=api.raw_io.output('')) +
        api.step_data(
            'read SKIMAGE_VERSION',
            stdout=api.raw_io.output('42'))
      )

    if 'Perf' in builder:
      test_data += api.step_data(
          'exists skia_perf',
          stdout=api.raw_io.output(''))
    return test_data

  for mastername, slaves in builders.iteritems():
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
        if 'Test' in builder:
          test += api.step_data('gsutil cat TIMESTAMP_LAST_UPLOAD_COMPLETED',
                                stdout=api.raw_io.output('42'))
        if 'Android' in builder:
          test += api.step_data('has ccache?', retcode=1)
        if 'Android' in builder and ('Test' in builder or 'Perf' in builder):
          test += AndroidTestData(builder)
        if 'ChromeOS' in builder:
          test += api.step_data('read SKP_VERSION',
                                stdout=api.raw_io.output('42'))
          if 'Test' in builder:
            test += api.step_data('read SKIMAGE_VERSION',
                                  stdout=api.raw_io.output('42'))
        if 'Trybot' in builder:
          test += api.properties(issue=500,
                                 patchset=1,
                                 rietveld='https://codereview.chromium.org')
        if 'Win' in builder:
          test += api.platform('win', 64)
        yield test

  builder = 'Test-Ubuntu-GCC-ShuttleA-CPU-AVX-x86_64-Debug-Recipes'
  yield (
    api.test('failed_dm') +
    api.properties(buildername=builder,
                   mastername='client.skia',
                   slavename='skiabot-linux-tester-000',
                   buildnumber=6) +
    api.step_data('gsutil cat TIMESTAMP_LAST_UPLOAD_COMPLETED',
                  stdout=api.raw_io.output('42')) +
    api.step_data('dm', retcode=1)
  )

  yield (
    api.test('has_ccache_android') +
    api.properties(buildername='Build-Ubuntu-GCC-Arm7-Debug-Android',
                   mastername='client.skia.compile',
                   slavename='skiabot-linux-compile-000') +
    api.step_data('has ccache?', retcode=0,
                  stdout=api.raw_io.output('/usr/bin/ccache'))
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
    api.step_data('has ccache?', retcode=1) +
    AndroidTestData(builder) +
    api.step_data('read SKP_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.step_data('gsutil cat TIMESTAMP_LAST_UPLOAD_COMPLETED',
                  stdout=api.raw_io.output('42')) +
    api.step_data('read SKIMAGE_VERSION',
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
    api.step_data('has ccache?', retcode=1) +
    AndroidTestData(builder) +
    api.step_data('read SKP_VERSION',
                  stdout=api.raw_io.output('2')) +
    api.step_data('gsutil cat TIMESTAMP_LAST_UPLOAD_COMPLETED',
                  stdout=api.raw_io.output('42')) +
    api.step_data('read SKIMAGE_VERSION',
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
    api.step_data('has ccache?', retcode=1) +
    AndroidTestData(builder) +
    api.step_data('read SKP_VERSION',
                  retcode=1) +
    api.step_data('gsutil cat TIMESTAMP_LAST_UPLOAD_COMPLETED',
                  stdout=api.raw_io.output('42')) +
    api.step_data('read SKIMAGE_VERSION',
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
                   test_downloaded_skimage_version='2') +
    api.step_data('has ccache?', retcode=1) +
    AndroidTestData(builder) +
    api.step_data('read SKP_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.step_data('gsutil cat TIMESTAMP_LAST_UPLOAD_COMPLETED',
                  stdout=api.raw_io.output('42')) +
    api.step_data('read SKIMAGE_VERSION',
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
    api.test('missing_SKIMAGE_VERSION_device') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data('has ccache?', retcode=1) +
    AndroidTestData(builder) +
    api.step_data('read SKP_VERSION',
                  stdout=api.raw_io.output('42')) +
    api.step_data('gsutil cat TIMESTAMP_LAST_UPLOAD_COMPLETED',
                  stdout=api.raw_io.output('42')) +
    api.step_data('read SKIMAGE_VERSION',
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
    api.step_data('gsutil cat TIMESTAMP_LAST_UPLOAD_COMPLETED',
                  stdout=api.raw_io.output('42')) +
    api.path.exists(
        api.path['slave_build'].join('skia'),
        api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
    )
  )

  yield (
    api.test('missing_SKIMAGE_VERSION_host') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data('gsutil cat TIMESTAMP_LAST_UPLOAD_COMPLETED',
                  stdout=api.raw_io.output('42')) +
    api.step_data('Get downloaded SKIMAGE_VERSION', retcode=1) +
    api.path.exists(
        api.path['slave_build'].join('skia'),
        api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
    )
  )

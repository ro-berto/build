# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia builders.


from common.skia import builder_name_schema
from slave.skia import slaves_cfg


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


def _getMasterAndSlaveForBuilder(builder):
  # Filesystem access is okay here because it is executed on the testing
  # machine.
  import os

  masters_path = os.path.join(os.path.realpath(os.path.dirname(__file__)),
                              os.pardir, os.pardir, os.pardir, os.pardir,
                              'masters')
  adj_builder = builder_name_schema.GetWaterfallBot(builder)
  for master in os.listdir(masters_path):
    if master.startswith('master.client.skia'):
      adj_master = master[len('master.'):]
      slaves = slaves_cfg.get(adj_master)
      for slavename in slaves:
        if adj_builder in slaves[slavename]['builder']:
          return adj_master, slavename, slaves[slavename]


def GenTests(api):
  builders = [
    'Build-Ubuntu-GCC-Arm7-Debug-CrOS_Daisy',
    'Build-Ubuntu-GCC-x86_64-Debug',
    'Build-Ubuntu-GCC-x86_64-Release-Mesa',
    'Perf-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Release',
    'Test-ChromeOS-GCC-Daisy-CPU-NEON-Arm7-Release',
    'Perf-Win7-MSVC-ShuttleA-GPU-HD2000-x86-Release-Trybot',
    'Test-Android-GCC-GalaxyS4-GPU-SGX544-Arm7-Debug',
    'Test-Android-GCC-Nexus5-GPU-Adreno330-Arm7-Debug',
    'Test-Android-GCC-Nexus10-GPU-MaliT604-Arm7-Release',
    'Test-Android-GCC-NexusPlayer-GPU-PowerVR-x86-Debug',
    'Test-ChromeOS-GCC-Link-CPU-AVX-x86_64-Debug',
    'Test-Mac10.8-Clang-MacMini4.1-GPU-GeForce320M-x86_64-Debug',
    'Test-Ubuntu-GCC-ShuttleA-GPU-GTX550Ti-x86_64-Release-Valgrind',
    'Test-Ubuntu-GCC-ShuttleA-GPU-GTX550Ti-x86_64-Debug-ZeroGPUCache',
    'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug',
    'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug-Trybot',
    'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Release-TSAN',
    'Test-Win7-MSVC-ShuttleA-GPU-HD2000-x86-Release',
    'Test-Win7-MSVC-ShuttleA-GPU-HD2000-x86-Release-ANGLE',
    'Test-Win8-MSVC-ShuttleA-CPU-AVX-x86_64-Debug',
  ]

  def AndroidTestData(builder, slave_cfg):
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

  for builder in builders:
    mastername, slavename, slave_cfg = _getMasterAndSlaveForBuilder(builder)
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
    if 'Android' in builder:
      test += AndroidTestData(builder, slave_cfg)
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
                   mastername=mastername,
                   slavename=slavename,
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
  master, slave, slave_cfg = _getMasterAndSlaveForBuilder(builder)
  yield (
    api.test('failed_get_hashes') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data('has ccache?', retcode=1) +
    AndroidTestData(builder, slave_cfg) +
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

  builder = 'Test-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Debug'
  master, slave, slave_cfg = _getMasterAndSlaveForBuilder(builder)
  yield (
    api.test('download_and_push_skps') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123',
                   test_downloaded_skp_version='2') +
    api.step_data('has ccache?', retcode=1) +
    AndroidTestData(builder, slave_cfg) +
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

  builder = 'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug'
  master, slave, slave_cfg = _getMasterAndSlaveForBuilder(builder)
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

  builder = 'Test-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Debug'
  master, slave, slave_cfg = _getMasterAndSlaveForBuilder(builder)
  yield (
    api.test('missing_SKP_VERSION_device') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data('has ccache?', retcode=1) +
    AndroidTestData(builder, slave_cfg) +
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

  builder = 'Test-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Debug'
  master, slave, slave_cfg = _getMasterAndSlaveForBuilder(builder)
  yield (
    api.test('download_and_push_skimage') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123',
                   test_downloaded_skimage_version='2') +
    api.step_data('has ccache?', retcode=1) +
    AndroidTestData(builder, slave_cfg) +
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

  builder = 'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug'
  master, slave, slave_cfg = _getMasterAndSlaveForBuilder(builder)
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

  builder = 'Test-Android-GCC-Nexus7-GPU-Tegra3-Arm7-Debug'
  master, slave, slave_cfg = _getMasterAndSlaveForBuilder(builder)
  yield (
    api.test('missing_SKIMAGE_VERSION_device') +
    api.properties(buildername=builder,
                   mastername=master,
                   slavename=slave,
                   buildnumber=6,
                   revision='abc123') +
    api.step_data('has ccache?', retcode=1) +
    AndroidTestData(builder, slave_cfg) +
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

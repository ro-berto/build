# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia builders.


from common.skia import builder_name_schema
from slave.skia import slaves_cfg

import os


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
    'Build-Ubuntu13.10-GCC4.8-Arm7-Debug-CrOS_Daisy',
    'Build-Ubuntu13.10-GCC4.8-x86_64-Debug',
    'Perf-Android-Nexus7-Tegra3-Arm7-Release',
    'Perf-ChromeOS-Daisy-MaliT604-Arm7-Release',
    'Perf-Win7-ShuttleA-HD2000-x86-Release',
    'Perf-Win7-ShuttleA-HD2000-x86-Release-Trybot',
    'Test-Android-GalaxyS4-SGX544-Arm7-Debug',
    'Test-Android-Nexus10-MaliT604-Arm7-Release',
    'Test-Android-Xoom-Tegra2-Arm7-Debug',
    'Test-Android-Venue8-PowerVR-x86-Debug',
    'Test-ChromeOS-Alex-GMA3150-x86-Debug',
    'Test-ChromeOS-Link-HD4000-x86_64-Debug',
    'Test-Mac10.8-MacMini4.1-GeForce320M-x86_64-Debug',
    'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Release-Valgrind',
    'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Debug-ZeroGPUCache',
    'Test-Ubuntu13.10-GCE-NoGPU-x86_64-Debug',
    'Test-Ubuntu13.10-GCE-NoGPU-x86_64-Debug-Trybot',
    'Test-Ubuntu13.10-GCE-NoGPU-x86_64-Release-TSAN',
    'Test-Win7-ShuttleA-HD2000-x86-Release',
    'Test-Win7-ShuttleA-HD2000-x86-Release-ANGLE',
    'Test-Win7-ShuttleA-HD2000-x86_64-Release',
  ]

  def AndroidTestData(builder, slave_cfg):
    expected_serial = slave_cfg.get('serial', 'abc123')
    test_data = (
        api.override_step_data(
            'List adb devices',
            api.json.output([expected_serial])) +
        api.step_data(
            'get EXTERNAL_STORAGE dir',
            stdout=api.raw_io.output('/storage/emulated/legacy')) +
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_skp/skps',
            stdout=api.raw_io.output(''))
    )
    if 'Test' in builder:
      test_data += (
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_gm_actual',
            stdout=api.raw_io.output('')) +
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_gm_expected',
            stdout=api.raw_io.output('')) +
        api.step_data(
            ('exists /storage/emulated/legacy/skiabot/skia_gm_expected/' +
             builder),
            stdout=api.raw_io.output('')) +
        api.step_data(
            ('exists /storage/emulated/legacy/skiabot/skia_gm_expected/' +
             builder + '/expected-results.json'),
            stdout=api.raw_io.output('')) +
        api.step_data(
            ('exists /storage/emulated/legacy/skiabot/skia_gm_expected/'
             'ignored-tests.txt'),
            stdout=api.raw_io.output('')) +
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_skimage_out/images',
            stdout=api.raw_io.output('')) +
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_skimage_out/%s' %
                 builder,
            stdout=api.raw_io.output('')) +
        api.step_data(
            ('exists /storage/emulated/legacy/skiabot/skia_skimage_expected/' +
             builder),
            stdout=api.raw_io.output(''))
      )

    if 'Perf' in builder:
      test_data += api.step_data(
          'exists /storage/emulated/legacy/skiabot/skia_perf',
          stdout=api.raw_io.output(''))
    return test_data

  for builder in builders:
    mastername, slavename, slave_cfg = _getMasterAndSlaveForBuilder(builder)
    test = (
      api.test(builder) +
      api.properties(buildername=builder,
                     mastername=mastername,
                     slavename=slavename,
                     buildnumber=5) +
      api.path.exists(
          api.path['slave_build'].join(
              'skia', 'expectations', 'gm',
              builder_name_schema.GetWaterfallBot(builder),
              'expected-results.json'),
          api.path['slave_build'].join('skia', 'expectations', 'gm',
                                       'ignored-tests.txt'),
          api.path['slave_build'].join('skia', 'expectations', 'skimage',
                                       builder, 'expected-results.json'),
          api.path['slave_build'].join('playback', 'skps', 'SKP_VERSION')
      )
    )
    if 'Android' in builder or 'NaCl' in builder:
      test += api.step_data('has ccache?', retcode=1)
    if 'Android' in builder:
      test += AndroidTestData(builder, slave_cfg)
    if 'Trybot' in builder:
      test += api.properties(issue=500,
                             patchset=1,
                             rietveld='https://codereview.chromium.org')
    if 'Win' in builder:
      test += api.platform('win', 64)
    yield test

  builder = 'Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug-Recipes'
  yield (
    api.test('failed_gm') +
    api.properties(buildername=builder,
                   mastername=mastername,
                   slavename=slavename,
                   buildnumber=6) +
    api.path.exists(
        api.path['slave_build'].join('skia', 'expectations', 'skimage',
                                     builder, 'expected-results.json')
    ) +
    api.step_data('gm', retcode=1)
  )

  yield (
    api.test('has_ccache_android') +
    api.properties(buildername='Build-Ubuntu13.10-GCC4.8-Arm7-Debug-Android',
                   mastername=mastername,
                   slavename=slavename) +
    api.step_data('has ccache?', retcode=0,
                  stdout=api.raw_io.output('/usr/bin/ccache'))
  )

  yield (
    api.test('has_ccache_nacl') +
    api.properties(buildername='Build-Ubuntu13.10-GCC4.8-NaCl-Debug',
                   mastername=mastername,
                   slavename=slavename) +
    api.step_data('has ccache?', retcode=0,
                  stdout=api.raw_io.output('/usr/bin/ccache'))
  )

  yield (
    api.test('no_skimage_expectations') +
    api.properties(buildername=builder,
                   mastername=mastername,
                   slavename=slavename,
                   buildnumber=7) +
    api.step_data('assert skimage expectations', retcode=1)
  )

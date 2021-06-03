# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_perf

SPEC = {}


def _AddBuildSpec(name,
                  platform,
                  config_name='chromium_perf',
                  target_bits=64,
                  **kwargs):
  SPEC[name] = chromium_perf.BuildSpec(config_name, platform, target_bits,
                                       **kwargs)


def _AddIsolatedTestSpec(name,
                         platform,
                         parent_buildername=None,
                         parent_builder_group=None,
                         target_bits=64,
                         **kwargs):
  spec = chromium_perf.TestSpec(
      'chromium_perf',
      platform,
      target_bits,
      parent_buildername=parent_buildername,
      **kwargs)
  if parent_builder_group:
    spec = spec.evolve(parent_builder_group=parent_builder_group)
  SPEC[name] = spec


_AddIsolatedTestSpec(
    'android-nexus5x-perf-fyi',
    'android',
    parent_buildername='android-builder-perf',
    parent_builder_group='chromium.perf',
    target_bits=32)

_AddIsolatedTestSpec(
    'android-pixel2-perf-aab-fyi',
    'android',
    parent_buildername='android_arm64-builder-perf',
    parent_builder_group='chromium.perf')

_AddIsolatedTestSpec(
    'android-pixel2-perf-fyi',
    'android',
    parent_buildername='android_arm64-builder-perf',
    parent_builder_group='chromium.perf')

_AddBuildSpec('android-cfi-builder-perf-fyi', 'android', target_bits=32)

_AddBuildSpec('android_arm64-cfi-builder-perf-fyi', 'android')

_AddBuildSpec(
    'chromeos-kevin-builder-perf-fyi',
    'chromeos',
    target_bits=32,
    target_arch='arm',
    cros_boards='kevin',
    extra_gclient_apply_config=['arm'])

_AddBuildSpec(
    'fuchsia-builder-perf-fyi',
    'fuchsia',
    bisect_archive_build=True,
    target_bits=64,
    target_arch='arm',
    extra_gclient_apply_config=[
        'fuchsia_arm64',
        'fuchsia_internal',
        'fuchsia_no_emu_isolate',
    ])

_AddIsolatedTestSpec(
    'fuchsia-perf-fyi',
    'fuchsia',
    target_bits=64,
    target_arch='arm',
    parent_buildername='fuchsia-builder-perf-fyi',
    parent_builder_group='chromium.perf.fyi')

_AddIsolatedTestSpec(
    'linux-perf-fyi',
    'linux',
    parent_buildername='linux-builder-perf',
    parent_builder_group='chromium.perf')

_AddIsolatedTestSpec(
    'win-10_laptop_high_end-perf_Lenovo-P51',
    'win',
    parent_buildername='win64-builder-perf',
    parent_builder_group='chromium.perf')

_AddIsolatedTestSpec(
    'win-10_laptop_high_end-perf_Dell-Precision',
    'win',
    parent_buildername='win64-builder-perf',
    parent_builder_group='chromium.perf')

_AddIsolatedTestSpec(
    'win-10_laptop_low_end-perf_HP-Candidate',
    'win',
    parent_buildername='win64-builder-perf',
    parent_builder_group='chromium.perf')

_AddIsolatedTestSpec(
    'win-7_laptop_low_end_x32-perf_Acer-Aspire-5',
    'win',
    parent_buildername='win32-builder-perf',
    parent_builder_group='chromium.perf',
    target_bits=32)

_AddIsolatedTestSpec(
    'win-7_laptop_low_end_x32-perf-Lenovo-ThinkPad',
    'win',
    parent_buildername='win32-builder-perf',
    parent_builder_group='chromium.perf',
    target_bits=32)

_AddIsolatedTestSpec(
    'chromeos-kevin-perf-fyi',
    'chromeos',
    parent_buildername='chromeos-kevin-builder-perf-fyi',
    parent_builder_group='chromium.perf.fyi',
    target_bits=32,
    target_arch='arm',
    cros_boards='kevin')

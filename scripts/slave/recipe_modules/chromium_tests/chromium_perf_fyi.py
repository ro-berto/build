# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import chromium_perf
from . import steps

import DEPS
CHROMIUM_CONFIG_CTX = DEPS['chromium'].CONFIG_CTX
GCLIENT_CONFIG_CTX = DEPS['gclient'].CONFIG_CTX


SPEC = {
  'builders': {},
  'settings': chromium_perf.SPEC['settings'],
}


@CHROMIUM_CONFIG_CTX(includes=['chromium_win_clang_official', 'mb'])
def chromium_perf_clang(c):
  pass


@GCLIENT_CONFIG_CTX(includes=['chromium_perf'])
def chromium_perf_clang(c):
  pass


def _AddBuildSpec(name, platform, config_name='chromium_perf',
                  target_bits=64,
                  compile_targets=None, extra_compile_targets=None,
                  force_exparchive=False, run_sizes=True):
  SPEC['builders'][name] = chromium_perf.BuildSpec(
      config_name, platform, target_bits,
      compile_targets=compile_targets,
      extra_compile_targets=extra_compile_targets,
      force_exparchive=force_exparchive, run_sizes=run_sizes)


def _AddIsolatedTestSpec(name, platform,
                         parent_buildername=None, parent_mastername=None,
                         target_bits=64):
  spec = chromium_perf.TestSpec(
      'chromium_perf', platform, target_bits,
      parent_buildername=parent_buildername)
  if parent_mastername:
    spec['parent_mastername'] = parent_mastername
  elif not parent_buildername:
    spec['parent_mastername'] = 'chromium.perf' #pragma: no cover
  else:
    spec['parent_mastername'] = 'chromium.perf.fyi'

  SPEC['builders'][name] = spec


# TODO(crbug.com/828444): remove this builder once 'android-builder-perf'
# functions well.
_AddBuildSpec('Android Builder Perf FYI', 'android', target_bits=32,
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'monochrome_public_apk',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])

_AddIsolatedTestSpec('Android Nexus 5X Perf FYI',
      'android', parent_buildername='Android Builder Perf FYI', target_bits=32)

_AddBuildSpec('Android arm64 Builder Perf FYI', 'android',
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])

_AddBuildSpec('Android CFI Builder Perf FYI', 'android',
              target_bits=32,
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])
_AddBuildSpec('Android CFI arm64 Builder Perf FYI', 'android',
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])

_AddBuildSpec('Linux Compile Perf FYI', 'linux')
_AddBuildSpec('Mac Builder Perf FYI', 'mac')

_AddIsolatedTestSpec('Mojo Linux Perf', 'linux',
                     parent_buildername='Linux Compile Perf FYI')
_AddIsolatedTestSpec(
    'One Buildbot Step Test Builder', 'linux',
    parent_buildername='Linux Compile Perf FYI')

_AddIsolatedTestSpec('OBBS Mac 10.12 Perf', 'mac',
                     parent_buildername='Mac Builder Perf FYI')
_AddIsolatedTestSpec('android-pixel2-perf', 'android',
                     parent_buildername='Android Builder Perf FYI')
_AddIsolatedTestSpec('android-pixel2_webview-perf', 'android',
                     parent_buildername='Android Builder Perf FYI')
_AddIsolatedTestSpec('android-go_webview-perf', 'android',
                     parent_buildername='android-builder-perf',
                     parent_mastername='chromium.perf')


_AddIsolatedTestSpec('win-10_laptop_high_end-perf_Lenovo-P51', 'win',
                     parent_buildername='win64-builder-perf',
                     parent_mastername='chromium.perf')

_AddIsolatedTestSpec('win-10_laptop_high_end-perf_Dell-Precision', 'win',
                     parent_buildername='win64-builder-perf',
                     parent_mastername='chromium.perf')

_AddIsolatedTestSpec('win-7_laptop_low_end_x32-perf_Acer-Aspire-5', 'win',
                     parent_buildername='win32-builder-perf',
                     parent_mastername='chromium.perf',
                     target_bits=32)

_AddIsolatedTestSpec('win-7_laptop_low_end_x32-perf_Dell-Latitude', 'win',
                     parent_buildername='win32-builder-perf',
                     parent_mastername='chromium.perf',
                     target_bits=32)

_AddIsolatedTestSpec('win-7_laptop_low_end_x32-perf-Lenovo-ThinkPad', 'win',
                     parent_buildername='win32-builder-perf',
                     parent_mastername='chromium.perf',
                     target_bits=32)

_AddIsolatedTestSpec('Histogram Pipeline Linux Perf',
                     'linux',
                     parent_buildername='Linux Compile Perf FYI')

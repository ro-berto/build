# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

from . import steps

import DEPS
CHROMIUM_CONFIG_CTX = DEPS['chromium'].CONFIG_CTX
GCLIENT_CONFIG_CTX = DEPS['gclient'].CONFIG_CTX


builders = collections.defaultdict(dict)


SPEC = {
  'builders': {},
  'settings': {
    'build_gs_bucket': 'chrome-perf',
    # Bucket for storing builds for manual bisect
    'bisect_build_gs_bucket': 'chrome-test-builds',
    'bisect_build_gs_extra': 'official-by-commit',
    'bisect_builders': [],
  },
}


@CHROMIUM_CONFIG_CTX(includes=['chromium', 'official', 'mb',
                               'goma_hermetic_fallback'])
def chromium_perf(c):
  # Bisects may build using old toolchains, so goma_hermetic_fallback is
  # required. See https://codereview.chromium.org/1015633002
  c.clobber_before_runhooks = False

  # HACK(shinyak): In perf builder, goma often fails with 'reached max
  # number of active fail fallbacks'. In fail fast mode, we cannot make the
  # number infinite currently.
  #
  # After the goma side fix, this env should be removed.
  # See http://crbug.com/606987
  c.compile_py.goma_max_active_fail_fallback_tasks = 1024


def _BaseSpec(bot_type, config_name, platform, target_bits, tests,
              use_private_swarming_server, use_private_isolate_server,
              remove_system_webview=None):
  spec = {
    'bot_type': bot_type,
    'chromium_config': config_name,
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': target_bits,
    },
    'gclient_config': config_name,
    'testing': {
      'platform': 'linux' if platform == 'android' else platform,
    },
    'tests': tests,
  }

  if platform == 'android':
    spec['android_config'] = 'chromium_perf'
    spec['android_apply_config'] = ['use_devil_adb']
    spec['chromium_apply_config'] = ['android']
    spec['chromium_config_kwargs']['TARGET_ARCH'] = 'arm'
    spec['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
    spec['gclient_apply_config'] = ['android']

  # TODO(crbug.com/818319): always set these private servers after we migrate
  # all perf bots.
  if use_private_swarming_server:
    spec['swarming_server'] = 'https://chrome-swarming.appspot.com'
    spec['swarming_service_account'] = 'chrome-perf-buildbot'

  # TODO(crbug.com/818319): always set these private servers after we migrate
  # all perf bots.
  # This will get covered when we convert a builder to upload files to private
  # isolate server. (crbug.com/818319)
  if use_private_isolate_server: # pragma: no cover
    spec['isolate_server'] = 'chrome-isolated.appspot.com'
    spec['isolate_service_account'] = 'chrome-perf-buildbot'
  return spec


def BuildSpec(
  config_name, perf_id, platform, target_bits,
  compile_targets=None, extra_compile_targets=None, force_exparchive=False,
  run_sizes=True, use_private_swarming_server=False,
  use_private_isolate_server=False):
  if not compile_targets:
    compile_targets = ['chromium_builder_perf']

  tests = []
    # TODO: Run sizes on Android.
  if run_sizes and not platform == 'android':
    tests = [steps.SizesStep('https://chromeperf.appspot.com', perf_id)]

  spec = _BaseSpec(
      bot_type='builder',
      config_name=config_name,
      platform=platform,
      target_bits=target_bits,
      tests=tests,
      use_private_swarming_server=use_private_swarming_server,
      use_private_isolate_server=use_private_isolate_server,
  )

  spec['perf_isolate_lookup'] = True

  if force_exparchive:
    spec['force_exparchive'] = force_exparchive

  spec['compile_targets'] = compile_targets
  if extra_compile_targets:
    spec['compile_targets'] += extra_compile_targets

  return spec


def TestSpec(config_name, perf_id, platform, target_bits,
             parent_buildername=None, tests=None, remove_system_webview=None,
             use_private_swarming_server=False,
             use_private_isolate_server=False):
  spec = _BaseSpec(
      bot_type='tester',
      config_name=config_name,
      platform=platform,
      target_bits=target_bits,
      tests=tests or [],
      use_private_swarming_server=use_private_swarming_server,
      use_private_isolate_server=use_private_isolate_server,
      remove_system_webview=remove_system_webview,
  )

  if not parent_buildername:
    parent_buildername = builders[platform][target_bits]
  spec['parent_buildername'] = parent_buildername
  spec['perf-id'] = perf_id
  spec['results-url'] = 'https://chromeperf.appspot.com'

  return spec


def _AddIsolatedTestSpec(name, perf_id, platform, target_bits=64,
                         parent_buildername=None,
                         use_private_swarming_server=False,
                         use_private_isolate_server=False):
  spec = TestSpec('chromium_perf', perf_id, platform, target_bits,
                  parent_buildername=parent_buildername,
                  use_private_swarming_server=use_private_swarming_server,
                  use_private_isolate_server=use_private_isolate_server)
  SPEC['builders'][name] = spec


def _AddBuildSpec(
  name, platform, target_bits=64, add_to_bisect=False,
  extra_compile_targets=None, force_exparchive=False):
  if target_bits == 64:
    perf_id = platform
  else:
    perf_id = '%s-%d' % (platform, target_bits)

  SPEC['builders'][name] = BuildSpec(
      'chromium_perf', perf_id, platform, target_bits,
      extra_compile_targets=extra_compile_targets,
      force_exparchive=force_exparchive)

  # TODO(martiniss): re-enable assertion once android has switched to the
  # chromium recipe
  # assert target_bits not in builders[platform]

  if not builders[platform].get(target_bits, None):
    builders[platform][target_bits] = name
  if add_to_bisect:
    SPEC['settings']['bisect_builders'].append(name)


_AddBuildSpec('Android Builder Perf', 'android', target_bits=32)
_AddBuildSpec('Android arm64 Builder Perf', 'android')
_AddBuildSpec('Android Compile Perf', 'android', target_bits=32,
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'dump_syms',
                                     'gpu_perftests',
                                     'microdump_stackwalk',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])
_AddBuildSpec('Android arm64 Compile Perf', 'android',
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])
_AddBuildSpec(
  'Win Builder Perf', 'win', target_bits=32, force_exparchive=True)
_AddBuildSpec(
  'Win x64 Builder Perf', 'win', add_to_bisect=True, force_exparchive=True)
_AddBuildSpec(
  'Mac Builder Perf', 'mac', add_to_bisect=True, force_exparchive=True)
_AddBuildSpec(
  'Linux Builder Perf', 'linux', add_to_bisect=True, force_exparchive=True)


# 32 bit android swarming
_AddIsolatedTestSpec('Android Nexus5X Perf', 'android-nexus5X', 'android',
                     parent_buildername='Android Compile Perf', target_bits=32,
                     use_private_swarming_server=True)
_AddIsolatedTestSpec('Android Nexus5 Perf', 'android-nexus5', 'android',
                     target_bits=32, parent_buildername='Android Compile Perf',
                     use_private_swarming_server=True)
_AddIsolatedTestSpec('Android One Perf', 'android-one', 'android',
                     target_bits=32, parent_buildername='Android Compile Perf',
                     use_private_swarming_server=True)

# Webview
_AddIsolatedTestSpec('Android Nexus5X WebView Perf', 'android-webview-nexus5X',
                     'android', parent_buildername='Android arm64 Compile Perf',
                     use_private_swarming_server=True)
_AddIsolatedTestSpec('Android Nexus6 WebView Perf', 'android-webview-nexus6',
                     'android', target_bits=32,
                     parent_buildername='Android Compile Perf',
                     use_private_swarming_server=True)


_AddIsolatedTestSpec('Win 10 High-DPI Perf', 'win-high-dpi', 'win',
                      use_private_swarming_server=True)
_AddIsolatedTestSpec('Win 10 Perf', 'chromium-rel-win10', 'win',
                      use_private_swarming_server=True)
_AddIsolatedTestSpec('Win 7 Perf', 'chromium-rel-win7-dual', 'win',
                     target_bits=32, use_private_swarming_server=True)
_AddIsolatedTestSpec('Win 7 Nvidia GPU Perf', 'chromium-rel-win7-gpu-nvidia',
                     'win', use_private_swarming_server=True)


_AddIsolatedTestSpec('mac-10_12_laptop_low_end-perf', '', 'mac',
                     use_private_swarming_server=True)
_AddIsolatedTestSpec('mac-10_13_laptop_high_end-perf', '', 'mac',
                     use_private_swarming_server=True)


_AddIsolatedTestSpec('linux-perf', '', 'linux',
    use_private_swarming_server=True)

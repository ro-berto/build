# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

RESULTS_URL = 'https://chromeperf.appspot.com'


def config(name,
           android_config=None,
           build_config='Release',
           chromium_config='clang_tot_linux',
           ninja_confirm_noop=True,
           is_msan=False,
           target_arch='intel',
           target_bits=64):
  cfg = {
    'chromium_config': chromium_config,
    'chromium_apply_config': [
      'mb',
    ],
    'gclient_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': build_config,
      'TARGET_ARCH': target_arch,
      'TARGET_BITS': target_bits,
    },
    'bot_type': 'builder_tester',
    'test_results_config': 'staging_server',
    'testing': {
      'platform': 'linux',
    },
    'tests': {
      steps.SizesStep(RESULTS_URL, name)
    },

    # TODO(dpranke): Get rid of this flag, it's a misfeature. This was
    # added to allow the bots to run `ninja` instead of `ninja all`
    # or `ninja all base_unittests net_unittests...`, but really the
    # compile() call in the recipe should be smart enough to do this
    # automatically. This shouldn't be configurable per bot.
    'add_tests_as_compile_targets': False,

    'enable_swarming': True,
  }

  if android_config:
      cfg['android_config'] = android_config
      cfg['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
      cfg['gclient_apply_config'] = ['android']

  if ninja_confirm_noop:
      cfg['chromium_apply_config'].append('ninja_confirm_noop')

  if is_msan:
      cfg['chromium_apply_config'].append('prebuilt_instrumented_libraries')

  return name, cfg


SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-clang-archive',
  },
  'builders': {
  },
}


SPEC['builders'].update([
    config('ToTAndroid',
           android_config='clang_tot_release_builder',
           chromium_config='clang_tot_android',
           ninja_confirm_noop=False,
           target_arch='arm',
           target_bits=32),

    config('ToTAndroid64',
           android_config='clang_tot_release_builder',
           chromium_config='clang_tot_android',
           ninja_confirm_noop=False,
           target_arch='arm',
           target_bits=64),

    config('ToTLinux'),

    config('ToTLinux (dbg)',
           build_config='Debug'),

    config('ToTLinuxASan',
           chromium_config='clang_tot_linux_asan'),

    config('ToTLinuxLLD',
           chromium_config='clang_tot_linux_lld'),

    config('ToTLinuxMSan',
           is_msan=True),

    config('ToTLinuxThinLTO',
           chromium_config='clang_tot_linux_lld'),

    config('ToTLinuxUBSanVptr',
           chromium_config='clang_tot_linux_ubsan_vptr'),
])

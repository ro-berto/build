# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')
def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')
def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')

defaults['category'] = '1clobber'

# Global scheduler
S('chromium', branch='src', treeStableTimer=60)

# Create the triggerable scheduler for the reliability tests.
T('reliability')

################################################################################
## Windows
################################################################################

B('Win', 'win_clobber', 'compile|windows', 'chromium', notify_on_missing=True)
F('win_clobber', win().ChromiumFactory(
    clobber=True,
    project='all.sln',
    tests=['sizes', 'reliability', 'check_bins'],
    factory_properties={'archive_build': True,
                        'gs_bucket': 'gs://chromium-browser-snapshots',
                        'extra_archive_paths': 'ceee,chrome_frame',
                        'show_perf_results': True,
                        'perf_id': 'chromium-rel-xp',
                        'expectations': True,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Win Reliability', 'win_reliability', '', 'reliability',
  notify_on_missing=True)
F('win_reliability', linux().ReliabilityTestsFactory())

################################################################################
## Mac
################################################################################

B('Mac', 'mac_clobber', 'compile|testers', 'chromium', notify_on_missing=True)
F('mac_clobber', mac().ChromiumFactory(
    clobber=True,
    tests=['sizes'],
    options=['--compiler=goma-clang'],
    factory_properties={'archive_build': True,
                        'gs_bucket': 'gs://chromium-browser-snapshots',
                        'show_perf_results': True,
                        'perf_id': 'chromium-rel-mac',
                        'expectations': True,
                        'gclient_env': {
                            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1'
                         },
                        'generate_gtest_json': True}))

################################################################################
## Linux
################################################################################

# For now we will assume a fixed toolchain location on the builders.
crosstool_prefix = (
    '/usr/local/crosstool-trusted/arm-crosstool/bin/arm-none-linux-gnueabi')
# Factory properties to use for an arm build.
arm_gclient_env = {
  'AR': crosstool_prefix + '-ar',
  'AS': crosstool_prefix + '-as',
  'CC': crosstool_prefix + '-gcc',
  'CXX': crosstool_prefix + '-g++',
  'LD': crosstool_prefix + '-ld',
  'RANLIB': crosstool_prefix + '-ranlib',
  'GYP_GENERATORS': 'make',
  'GYP_DEFINES': (
      'target_arch=arm '
      'sysroot=/usr/local/arm-rootfs '
      'disable_nacl=1 '
      'linux_use_tcmalloc=0 '
      'armv7=1 '
      'arm_thumb=1 '
      'arm_neon=0 '
      'arm_fpu=vfpv3-d16 '
      'chromeos=1 '  # Since this is the intersting variation.
  ),
}

B('Linux', 'linux_clobber', 'compile|testers', 'chromium',
  notify_on_missing=True)
F('linux_clobber', linux().ChromiumFactory(
    clobber=True,
    tests=['sizes', 'check_perms', 'check_licenses'],
    options=['--compiler=goma'],
    factory_properties={'archive_build': True,
                        'gs_bucket': 'gs://chromium-browser-snapshots',
                        'show_perf_results': True,
                        'perf_id': 'chromium-rel-linux',
                        'expectations': True,
                        'generate_gtest_json': True,
                        'gclient_env': {'GYP_DEFINES':'target_arch=ia32'},}))

B('Linux x64', 'linux64_clobber', 'compile|testers', 'chromium',
  notify_on_missing=True)
F('linux64_clobber', linux().ChromiumFactory(
    clobber=True,
    tests=['sizes'],
    options=['--compiler=goma'],
    factory_properties={
        'archive_build': True,
        'gs_bucket': 'gs://chromium-browser-snapshots',
        'show_perf_results': True,
        'generate_gtest_json': True,
        'perf_id': 'chromium-rel-linux-64',
        'expectations': True,
        'gclient_env': {'GYP_DEFINES':'target_arch=x64'}}))

def Update(config, active_master, c):
  return helper.Update(c)

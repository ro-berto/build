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

defaults['category'] = '1full'

# Global scheduler
S('chromium', branch='src', treeStableTimer=60)

# Create the triggerable scheduler for the reliability tests.
T('reliability')

################################################################################
## Windows
################################################################################

B('Win', 'win_full', 'compile|windows', 'chromium')
F('win_full', win().ChromiumFactory(
    clobber=True,
    project='all.sln',
    tests=['sizes', 'selenium', 'unit', 'ui', 'test_shell', 'memory',
           'reliability', 'printing', 'remoting', 'check_deps',
           'browser_tests', 'courgette', 'check_bins', 'webkit_unit',
           'chrome_frame_unittests', 'gpu', 'installer'],
    factory_properties={'archive_build': True,
                        'extra_archive_paths': 'ceee,chrome_frame',
                        'show_perf_results': True,
                        'perf_id': 'chromium-rel-xp',
                        'expectations': True,
                        'process_dumps': True,
                        'start_crash_handler': True,
                        'generate_gtest_json': True}))

B('Win Reliability', 'win_reliability', '', 'reliability')
F('win_reliability', linux().ReliabilityTestsFactory())

################################################################################
## Mac
################################################################################

B('Mac', 'mac_full', 'compile|testers', 'chromium')
F('mac_full', mac().ChromiumFactory(
    clobber=True,
    tests=['sizes', 'unit', 'ui', 'dom_checker', 'test_shell', 'memory',
           'printing', 'remoting', 'browser_tests', 'webkit_unit', 'gpu'],
    factory_properties={'archive_build': True,
                        'show_perf_results': True,
                        'perf_id': 'chromium-rel-mac',
                        'expectations': True,
                        'generate_gtest_json': True}))

################################################################################
## Linux
################################################################################

# For now we will assume a fixed toolchain location on the builders.
crosstool_prefix = (
    '/usr/local/crosstool-trusted/arm-2009q3/bin/arm-none-linux-gnueabi')
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

B('Linux', 'linux_full', 'compile|testers', 'chromium')
F('linux_full', linux().ChromiumFactory(
    clobber=True,
    tests=['unit', 'ui', 'dom_checker', 'googleurl', 'media', 'printing',
           'remoting', 'sizes', 'test_shell', 'memory', 'browser_tests',
           'webkit_unit', 'nacl_ui', 'nacl_sandbox', 'gpu', 'check_perms'],
    factory_properties={'archive_build': True,
                        'show_perf_results': True,
                        'perf_id': 'chromium-rel-linux',
                        'expectations': True,
                        'generate_gtest_json': True,}))

B('Linux x64', 'linux64_full', 'compile|testers', 'chromium')
F('linux64_full', linux().ChromiumFactory(
    clobber=True,
    tests=['base', 'net', 'unit', 'ui', 'dom_checker', 'googleurl', 'media',
           'printing', 'remoting', 'sizes', 'test_shell', 'memory',
           'browser_tests', 'webkit_unit', 'gpu'],
    factory_properties={
        'archive_build': True,
        'show_perf_results': True,
        'generate_gtest_json': True,
        'perf_id': 'chromium-rel-linux-64',
        'expectations': True,
        'gclient_env': {'GYP_DEFINES':'target_arch=x64'}}))

B('Arm', 'arm_full', 'compile|testers', 'chromium')
F('arm_full', linux().ChromiumOSFactory(
    clobber=True,
    target='Release',
    tests=[],
    compile_timeout=3600,
    options=['--build-tool=make',
             '--crosstool=' + crosstool_prefix,
             'chromeos_builder'],
    factory_properties={'archive_build': True,
                        'gclient_env': arm_gclient_env}))

def Update(config, active_master, c):
  return helper.Update(c)

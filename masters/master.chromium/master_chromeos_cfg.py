# Copyright (c) 2010 The Chromium Authors. All rights reserved.
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

def chromeos(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '8chromiumos'

#
# Main debug scheduler for src/
#
S('chromeos_rel', branch='src', treeStableTimer=60)

#
# ChromeOS Rel Builder
#
B('Linux Builder (ChromiumOS)', 'rel', 'compile', 'chromeos_rel')
F('rel', chromeos().ChromiumOSFactory(
    tests=['unit', 'base', 'net', 'googleurl', 'media', 'ui', 'printing',
           'remoting', 'browser_tests', 'interactive_ui', 'views'],
    options=['chromeos_builder'],
    factory_properties={
        'archive_build': True,
        'extra_archive_paths': 'chrome/tools/build/chromeos',
        'gclient_env': { 'GYP_DEFINES':'chromeos=1'},
        'generate_gtest_json': True}))


################################################################################
## Debug
################################################################################

#
# Main debug scheduler for src/
#
S('chromeos_dbg', branch='src', treeStableTimer=60)

#
# ChromeOS Dbg Builder
#
B('Linux Builder (ChromiumOS dbg)', 'cros_dbg', 'compile', 'chromeos_dbg')
F('cros_dbg', chromeos().ChromiumOSFactory(
    target='Debug',
    tests=['unit', 'base', 'net', 'googleurl', 'media', 'ui', 'printing',
           'remoting', 'browser_tests', 'interactive_ui', 'views'],
    options=['chromeos_builder'],
    factory_properties={
        'gclient_env': { 'GYP_DEFINES':'chromeos=1'},
        'generate_gtest_json': True}))

B('Linux Builder (Views dbg)', 'view_dbg', 'compile', 'chromeos_dbg')
F('view_dbg', chromeos().ChromiumOSFactory(
    target='Debug',
    tests=['unit', 'base', 'net', 'googleurl', 'media', 'ui', 'printing',
           'remoting', 'browser_tests', 'interactive_ui', 'views'],
    options=['app_unittests', 'base_unittests', 'browser_tests',
             'interactive_ui_tests', 'ipc_tests', 'googleurl_unittests',
             'media_unittests', 'net_unittests', 'printing_unittests',
             'remoting_unittests', 'sync_unit_tests', 'ui_tests', 'unit_tests',
             'views_unittests'],
    factory_properties={'gclient_env': { 'GYP_DEFINES':'toolkit_views=1'},
                        'generate_gtest_json': True}))


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
arm_dbg_factory_properties = {
  'archive_build': False,
  'gclient_env': arm_gclient_env,
}

B('Arm (dbg)', 'arm_dbg', 'compile', 'chromeos_dbg')
F('arm_dbg', chromeos().ChromiumOSFactory(
    clobber=True,
    target='Debug',
    tests=[],
    compile_timeout=14400,
    options=[
      '--build-tool=make',
      '--crosstool=' + crosstool_prefix,
      'chromeos_builder',
    ],
    factory_properties=arm_dbg_factory_properties))

def Update(config, active_master, c):
  return helper.Update(c)

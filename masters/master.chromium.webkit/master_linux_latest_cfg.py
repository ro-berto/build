# Copyright (c) 2012 The Chromium Authors. All rights reserved.
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

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '9linux latest'

#
# Main release scheduler for webkit
#
S('s9_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Linux Rel tests
#
B('Linux Tests', 'f_linux_tests_rel', auto_reboot=True,
  scheduler='s9_webkit_rel')
F('f_linux_tests_rel', linux().ChromiumWebkitLatestFactory(
    tests=[
      'browser_tests',
      'interactive_ui',
      'unit',
    ],
    options=['--compiler=goma'],
    factory_properties={'generate_gtest_json': True}))

B('Linux Perf', 'f_linux_perf_rel', auto_reboot=True,
  scheduler='s9_webkit_rel')
F('f_linux_perf_rel', linux().ChromiumWebkitLatestFactory(
    options=['--compiler=goma', 'chromium_builder_perf'],
    tests=[
      'dom_perf',
      'dromaeo',
      'page_cycler_bloat-http',
      'page_cycler_database',
      'page_cycler_dhtml',
      'page_cycler_indexeddb',
      'page_cycler_intl1',
      'page_cycler_intl2',
      'page_cycler_morejs',
      'page_cycler_moz',
      'page_cycler_moz-http',
      'startup',
      'sunspider'
    ],
    factory_properties={'perf_id': 'chromium-rel-linux-webkit',
                        'show_perf_results': True,}))

valgrind_gyp_defines = chromium_factory.ChromiumFactory.MEMORY_TOOLS_GYP_DEFINES
B('Linux Valgrind', 'f_linux_valgrind_rel', auto_reboot=True,
  scheduler='s9_webkit_rel')
F('f_linux_valgrind_rel', linux().ChromiumWebkitLatestFactory(
    options=['--compiler=goma', 'test_shell', 'test_shell_tests'],
    tests=['valgrind_test_shell'],
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {'GYP_DEFINES' : valgrind_gyp_defines,}}))


def Update(config, active_master, c):
  return helper.Update(c)

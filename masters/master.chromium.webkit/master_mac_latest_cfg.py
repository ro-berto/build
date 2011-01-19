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

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = '8mac latest'

#
# Main release schedulers for chromium and webkit
#
S('s8_chromium_rel', branch='src', treeStableTimer=60)
S('s8_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Mac Rel Builder
#
B('Mac10.6 Tests', 'f_mac_tests_rel',
  scheduler='s8_chromium_rel|s8_webkit_rel')
F('f_mac_tests_rel', mac().ChromiumWebkitLatestFactory(
    options=['--', '-target', 'chromium_builder_tests'],
    tests=['browser_tests', 'interactive_ui', 'nacl_ui', 'unit', 'ui'],
    factory_properties={'generate_gtest_json': True}))

B('Mac10.6 Perf', 'f_mac_perf6_rel',
  scheduler='s8_chromium_rel|s8_webkit_rel')
F('f_mac_perf6_rel', mac().ChromiumWebkitLatestFactory(
    options=['--', '-target', 'chromium_builder_tests'],
    tests=['dom_perf', 'dromaeo', 'memory', 'page_cycler', 'page_cycler_http',
           'startup', 'sunspider', 'tab_switching', 'v8_benchmark'],
    factory_properties={'show_perf_results': True,
                        'perf_id': 'chromium-rel-mac6-webkit'}))

################################################################################
## Debug
################################################################################

#
# Main debug schedulers for chromium and webkit
#
S('s8_chromium_dbg', branch='src', treeStableTimer=60)
S('s8_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Mac Dbg Builder
#
B('Mac Clang Builder (dbg)', 'f_mac_clang_dbg',
  scheduler='s8_chromium_dbg|s8_webkit_dbg')
F('f_mac_clang_dbg', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    options=['--compiler=clang',
             '--', '-project', '../webkit/webkit.xcodeproj',],
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'clang=1'}}))

def Update(config, active_master, c):
  return helper.Update(c)

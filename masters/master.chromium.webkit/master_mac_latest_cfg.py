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

def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = '8mac latest'

#
# Main release scheduler for webkit
#
S('s8_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Mac Rel Builder
#
B('Mac10.6 Tests', 'f_mac_tests_rel', scheduler='s8_webkit_rel')
F('f_mac_tests_rel', mac().ChromiumWebkitLatestFactory(
    options=['--compiler=clang', '--', '-target', 'chromium_builder_tests'],
    tests=['browser_tests', 'interactive_ui', 'nacl_ui', 'unit', 'ui'],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1'
        },
    }))

B('Mac10.6 Perf', 'f_mac_perf6_rel', scheduler='s8_webkit_rel')
F('f_mac_perf6_rel', mac().ChromiumWebkitLatestFactory(
    options=['--compiler=clang', '--', '-target', 'chromium_builder_perf'],
    tests=['dom_perf', 'dromaeo', 'memory', 'page_cycler', 'page_cycler_http',
           'startup', 'sunspider', 'tab_switching', 'v8_benchmark'],
    factory_properties={
        'show_perf_results': True,
        'perf_id': 'chromium-rel-mac6-webkit',
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1'
        },
    }))

################################################################################
## Debug
################################################################################

#
# Main debug scheduler for webkit
#
S('s8_webkit_dbg', branch='trunk', treeStableTimer=60)

#
# Mac Dbg Builder
#
B('Mac Gcc Builder (dbg)', 'f_mac_gcc_dbg',
  scheduler='s8_webkit_dbg')
F('f_mac_gcc_dbg', mac().ChromiumWebkitLatestFactory(
    target='Debug',
    options=['--', '-project', '../webkit/webkit.xcodeproj',]))

def Update(config, active_master, c):
  return helper.Update(c)

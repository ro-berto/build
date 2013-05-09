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

def linux(): return chromium_factory.ChromiumFactory('src/out', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = 'nonlayout'

#
# Main release scheduler for webkit
#
S('s9_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Linux Rel tests
#
B('Linux Tests', 'f_linux_tests_rel', scheduler='s9_webkit_rel')
F('f_linux_tests_rel', linux().ChromiumFactory(
    tests=[
        'browser_tests',
        'cc_unittests',
        'content_browsertests',
        'interactive_ui_tests',
        'unit',
        'webkit_compositor_bindings_unittests',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma'
    ],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
        'blink_config': 'blink',
    }))

linux_aura_build_targets = [
    'aura_builder',
    'base_unittests',
    'browser_tests',
    'cacheinvalidation_unittests',
    'compositor_unittests',
    'content_browsertests',
    'content_unittests',
    'crypto_unittests',
    'device_unittests',
    'gpu_unittests',
    'interactive_ui_tests',
    'ipc_tests',
    'jingle_unittests',
    'media_unittests',
    'net_unittests',
    'ppapi_unittests',
    'printing_unittests',
    'remoting_unittests',
    'sql_unittests',
    'ui_unittests',
    'url_unittests',
]

B('Linux Aura', 'f_linux_aura_rel', scheduler='s9_webkit_rel')
F('f_linux_aura_rel', linux().ChromiumFactory(
    tests=[
        'aura',
        # This seems to have many failures
        #'content_browsertests',
        'unit',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
    ] + linux_aura_build_targets,
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': {'GYP_DEFINES': 'use_aura=1', 'GYP_GENERATORS': 'ninja'},
        'window_manager': 'False',
        'blink_config': 'blink',
    }))

B('Linux Perf', 'f_linux_perf_rel', scheduler='s9_webkit_rel')
F('f_linux_perf_rel', linux().ChromiumFactory(
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'chromium_builder_perf'
    ],
    tests=[
        'dom_perf',
        'dromaeo',
        'page_cycler_bloat',
        'page_cycler_dhtml',
        'page_cycler_indexeddb',
        'page_cycler_intl1',
        'page_cycler_intl2',
        'page_cycler_morejs',
        'page_cycler_moz',
        'startup',
        'sunspider'
    ],
    factory_properties={
        'perf_id': 'chromium-rel-linux-webkit',
        'show_perf_results': True,
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
        'blink_config': 'blink',
    }))

def Update(config, active_master, c):
  return helper.Update(c)

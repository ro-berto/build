# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

import config

ActiveMaster = config.Master.ChromiumWebkit

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

defaults['category'] = '3webkit linux deps'

#
# Main release scheduler for chromium
#
S('s3_chromium_rel', branch='src', treeStableTimer=60)

#
# Linux Rel Builder
#
B('WebKit Linux (deps)', 'f_webkit_linux_rel', scheduler='s3_chromium_rel')
F('f_webkit_linux_rel', linux().ChromiumFactory(
    tests=[
        'webkit',
        'webkit_lint',
        'webkit_unit',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'content_shell',
        'DumpRenderTree',
        'test_shell',
        'webkit_unit_tests',
    ],
    factory_properties={
        'additional_expectations': [
            ['webkit', 'tools', 'layout_tests', 'test_expectations.txt' ],
        ],
        'archive_webkit_results': ActiveMaster.is_production_host,
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
    }))

def Update(_config, active_master, c):
  return helper.Update(c)

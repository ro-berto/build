# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import chromium_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = 'content'

#
# Content Shell Layouttests
#

B('WebKit (Content Shell) Linux', 'f_contentshell_linux_rel',
  scheduler='global_scheduler')

F('f_contentshell_linux_rel', linux().ChromiumFactory(
    target='Release',
    tests=[
        'webkit',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'content_shell_builder',
    ],
    factory_properties={
        'additional_drt_flag': '--dump-render-tree',
        'additional_expectations': [
            [ 'third_party',
              'WebKit',
              'LayoutTests',
              'platform',
              'chromium',
              'ContentShellTestExpectations' ],
        ],
        'archive_webkit_results': ActiveMaster.is_production_host,
        'driver_name': 'content_shell',
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))


def Update(_config, _active_master, c):
  return helper.Update(c)

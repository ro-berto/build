# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '9content shell'

#
# Main release scheduler for webkit
#
S('s9_contentshell_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Content Shell Layouttests
#

B('Linux (Content Shell)',
  'f_contentshell_linux_rel',
  scheduler='s9_contentshell_webkit_rel',
  auto_reboot=True)

F('f_contentshell_linux_rel', linux().ChromiumWebkitLatestFactory(
    tests=[
      'webkit',
    ],
    options=[
      '--compiler=goma',
      'content_shell',
      'ImageDiff',
    ],
    factory_properties={
      'additional_drt_flag': '--dump-render-tree',
      'archive_webkit_results': True,
      'test_results_server': 'test-results.appspot.com',
      'driver_name': 'content_shell'
    }))


def Update(config, active_master, c):
  return helper.Update(c)

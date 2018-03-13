# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import remote_run_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)

defaults['category'] = 'layout'

################################################################################
## Release
################################################################################

#
# Mac Rel Builder
#

B('WebKit Mac Builder', 'f_webkit_mac_rel',
  auto_reboot=False, scheduler='global_scheduler',
  builddir='webkit-mac-latest-rel')
F('f_webkit_mac_rel', m_remote_run('chromium'))

#
# Mac Rel WebKit testers
#

B('WebKit Mac10.10', 'f_webkit_rel_tests_1010')
F('f_webkit_rel_tests_1010', m_remote_run('chromium'))

B('WebKit Mac10.11', 'f_webkit_rel_tests_1011')
F('f_webkit_rel_tests_1011', m_remote_run('chromium'))

B('WebKit Mac10.12', 'f_webkit_rel_tests_1012')
F('f_webkit_rel_tests_1012', m_remote_run('chromium'))

B('WebKit Mac10.12 (retina)', 'f_webkit_rel_tests_1012_retina')
F('f_webkit_rel_tests_1012_retina', m_remote_run('chromium'))


################################################################################
## Debug
################################################################################

# Archive location
dbg_archive = master_config.GetGSUtilUrl('chromium-build-transfer',
                                         'WebKit Mac Builder (dbg)')

#
# Mac Dbg Builder
#
B('WebKit Mac Builder (dbg)', 'f_webkit_mac_dbg', auto_reboot=False,
  scheduler='global_scheduler', builddir='webkit-mac-latest-dbg')
F('f_webkit_mac_dbg', m_remote_run('chromium'))

#
# Mac Dbg WebKit testers
#

B('WebKit Mac10.11 (dbg)', 'f_webkit_dbg_tests')
F('f_webkit_dbg_tests', m_remote_run('chromium'))


################################################################################
##
################################################################################

def Update(_config, _active_master, c):
  return helper.Update(c)

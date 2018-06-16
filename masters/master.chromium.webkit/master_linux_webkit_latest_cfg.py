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
# Linux Rel Builder/Tester
#

B('WebKit Linux Trusty ASAN', 'f_webkit_linux_rel_asan',
    scheduler='global_scheduler', auto_reboot=True)
F('f_webkit_linux_rel_asan', m_remote_run('chromium'))

B('WebKit Linux Trusty MSAN', 'f_webkit_linux_rel_msan',
    scheduler='global_scheduler', auto_reboot=True)
F('f_webkit_linux_rel_msan', m_remote_run('chromium'))

B('WebKit Linux Trusty Leak', 'f_webkit_linux_leak_rel',
    scheduler='global_scheduler', category='layout')
F('f_webkit_linux_leak_rel', m_remote_run('chromium'))


def Update(_config, _active_master, c):
  return helper.Update(c)

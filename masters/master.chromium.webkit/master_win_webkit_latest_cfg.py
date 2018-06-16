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

# Archive location
rel_archive = master_config.GetGSUtilUrl('chromium-build-transfer',
                                         'WebKit Win Builder')

#
# Win Rel Builder
#
B('WebKit Win Builder', 'f_webkit_win_rel',
  scheduler='global_scheduler', builddir='webkit-win-latest-rel',
  auto_reboot=True)
F('f_webkit_win_rel', m_remote_run('chromium'))

#
# Win Rel WebKit testers
#
B('WebKit Win10', 'f_webkit_rel_tests')
F('f_webkit_rel_tests', m_remote_run('chromium'))


def Update(_config, _active_master, c):
  return helper.Update(c)

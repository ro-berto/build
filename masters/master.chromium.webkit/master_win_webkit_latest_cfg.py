# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties

from master import master_config
from master import master_utils
from master.factory import remote_run_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

revision_getter = master_utils.ConditionalProperty(
    lambda build: build.getProperty('revision'),
    WithProperties('%(revision)s'),
    'master')

def m_remote_run_chromium_src(recipe, **kwargs):
  kwargs.setdefault('revision', revision_getter)
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/src.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      use_gitiles=True,
      **kwargs)

defaults['category'] = 'layout'

################################################################################
## Release
################################################################################

# Archive location
rel_archive = master_config.GetGSUtilUrl('chromium-build-transfer',
                                         'WebKit Win Builder')

#
# Triggerable scheduler for testers
#
T('s4_webkit_rel_trigger')

#
# Win Rel Builder
#
B('WebKit Win Builder', 'f_webkit_win_rel',
  scheduler='global_scheduler', builddir='webkit-win-latest-rel',
  auto_reboot=False)
F('f_webkit_win_rel', m_remote_run_chromium_src(
    'chromium', triggers=['s4_webkit_rel_trigger']))

#
# Win Rel WebKit testers
#
B('WebKit Win7', 'f_webkit_rel_tests', scheduler='s4_webkit_rel_trigger')
B('WebKit Win10', 'f_webkit_rel_tests', scheduler='s4_webkit_rel_trigger')
F('f_webkit_rel_tests', m_remote_run_chromium_src('chromium'))

#
# Win x64 Rel Builder (note: currently no x64 testers)
#
B('WebKit Win x64 Builder', 'f_webkit_win_rel_x64',
  scheduler='global_scheduler', builddir='webkit-win-latest-rel-x64',
  auto_reboot=False)
F('f_webkit_win_rel_x64', m_remote_run_chromium_src('chromium'))


################################################################################
## Debug
################################################################################

#
# Triggerable scheduler for testers
#
T('s4_webkit_dbg_trigger')

#
# Win Dbg Builder
#
B('WebKit Win Builder (dbg)', 'f_webkit_win_dbg', scheduler='global_scheduler',
  builddir='webkit-win-latest-dbg', auto_reboot=False)
F('f_webkit_win_dbg', m_remote_run_chromium_src('chromium',
    triggers=['s4_webkit_dbg_trigger']))

#
# Win Dbg WebKit testers
#

B('WebKit Win7 (dbg)', 'f_webkit_dbg_tests',
    scheduler='s4_webkit_dbg_trigger')
F('f_webkit_dbg_tests', m_remote_run_chromium_src('chromium'))

#
# Win x64 Dbg Builder (note: currently no x64 testers)
#
B('WebKit Win x64 Builder (dbg)', 'f_webkit_win_dbg_x64',
  scheduler='global_scheduler', builddir='webkit-win-latest-dbg-x64',
  auto_reboot=False)
F('f_webkit_win_dbg_x64', m_remote_run_chromium_src('chromium'))

def Update(_config, _active_master, c):
  return helper.Update(c)

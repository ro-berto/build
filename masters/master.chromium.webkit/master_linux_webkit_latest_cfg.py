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

#
# Linux Rel Builder/Tester
#

B('WebKit Linux Trusty', 'f_webkit_linux_rel', scheduler='global_scheduler')
F('f_webkit_linux_rel', m_remote_run_chromium_src('chromium'))

B('WebKit Linux Trusty ASAN', 'f_webkit_linux_rel_asan',
    scheduler='global_scheduler', auto_reboot=True)
F('f_webkit_linux_rel_asan', m_remote_run_chromium_src('chromium'))

B('WebKit Linux Trusty MSAN', 'f_webkit_linux_rel_msan',
    scheduler='global_scheduler', auto_reboot=True)
F('f_webkit_linux_rel_msan', m_remote_run_chromium_src('chromium'))

B('WebKit Linux Trusty Leak', 'f_webkit_linux_leak_rel',
    scheduler='global_scheduler', category='layout')
F('f_webkit_linux_leak_rel', m_remote_run_chromium_src('chromium'))


################################################################################
## Debug
################################################################################

#
# Linux Dbg Webkit builders/testers
#

B('WebKit Linux Trusty (dbg)', 'f_webkit_dbg_tests',
    scheduler='global_scheduler', auto_reboot=True)
F('f_webkit_dbg_tests', m_remote_run_chromium_src('chromium'))


def Update(_config, _active_master, c):
  return helper.Update(c)

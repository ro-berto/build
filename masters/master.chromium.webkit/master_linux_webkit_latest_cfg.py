# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import annotator_factory
from master.factory import chromium_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')

m_annotator = annotator_factory.AnnotatorFactory()

defaults['category'] = 'layout'


################################################################################
## Release
################################################################################

#
# Linux Rel Builder/Tester
#
# FIXME: Rename this builder to indicate that it is running precise.
B('WebKit Linux', 'f_webkit_linux_rel', scheduler='global_scheduler')
F('f_webkit_linux_rel', m_annotator.BaseFactory('chromium'))

B('WebKit Linux Trusty', 'f_webkit_linux_rel_trusty',
    scheduler='global_scheduler')
F('f_webkit_linux_rel_trusty', m_annotator.BaseFactory('chromium'))

B('WebKit Linux 32', 'f_webkit_linux_rel_32', scheduler='global_scheduler')
F('f_webkit_linux_rel_32', m_annotator.BaseFactory('chromium'))

B('WebKit Linux Oilpan', 'f_webkit_linux_oilpan_rel',
    scheduler='global_scheduler', category='oilpan')
F('f_webkit_linux_oilpan_rel', m_annotator.BaseFactory('chromium'))

B('WebKit Linux ASAN', 'f_webkit_linux_rel_asan', scheduler='global_scheduler',
    auto_reboot=True)
F('f_webkit_linux_rel_asan', m_annotator.BaseFactory('chromium'))

B('WebKit Linux Oilpan ASAN', 'f_webkit_linux_oilpan_rel_asan',
    scheduler='global_scheduler', auto_reboot=True, category='oilpan')
F('f_webkit_linux_oilpan_rel_asan', m_annotator.BaseFactory('chromium'))

B('WebKit Linux MSAN', 'f_webkit_linux_rel_msan', scheduler='global_scheduler',
    auto_reboot=True)
F('f_webkit_linux_rel_msan', m_annotator.BaseFactory('chromium'))

B('WebKit Linux Leak', 'f_webkit_linux_leak_rel', scheduler='global_scheduler',
    category='oilpan')
F('f_webkit_linux_leak_rel', m_annotator.BaseFactory('chromium'))

B('WebKit Linux Oilpan Leak', 'f_webkit_linux_oilpan_leak_rel',
    scheduler='global_scheduler', category='oilpan')
F('f_webkit_linux_oilpan_leak_rel', m_annotator.BaseFactory('chromium'))


################################################################################
## Debug
################################################################################

#
# Linux Dbg Webkit builders/testers
#

B('WebKit Linux (dbg)', 'f_webkit_dbg_tests', scheduler='global_scheduler',
    auto_reboot=False)
F('f_webkit_dbg_tests', m_annotator.BaseFactory('chromium'))

B('WebKit Linux Oilpan (dbg)', 'f_webkit_linux_oilpan_dbg',
    scheduler='global_scheduler', category='oilpan')
F('f_webkit_linux_oilpan_dbg', m_annotator.BaseFactory('chromium'))


def Update(_config, _active_master, c):
  return helper.Update(c)

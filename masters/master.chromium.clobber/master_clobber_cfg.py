# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')
def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')
def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')

defaults['category'] = '1clobber'

# Global scheduler
S('chromium', branch='src', treeStableTimer=60, categories=['svnpoller'])

# Create the triggerable scheduler for the reliability tests.
T('reliability')

################################################################################
## Windows
################################################################################

B('Win', 'win_full', 'compile|windows', 'chromium')
F('win_full', win().ChromiumFactory(
    clobber=True,
    project='all.sln',
    factory_properties={'archive_build': True,
                        'extra_archive_paths': 'chrome_frame',
                        'gs_bucket': 'gs://chromium-browser-snapshots',}))

B('Win Reliability', 'win_reliability', '', 'reliability')
F('win_reliability', linux().ReliabilityTestsFactory())

################################################################################
## Mac
################################################################################

B('Mac', 'mac_full', 'compile|testers', 'chromium')
F('mac_full', mac().ChromiumFactory(
    clobber=True,
    factory_properties={'archive_build': True,
                        'gs_bucket': 'gs://chromium-browser-snapshots'}))

################################################################################
## Linux
################################################################################

B('Linux', 'linux_full', 'compile|testers', 'chromium')
F('linux_full', linux().ChromiumFactory(
    clobber=True,
    factory_properties={'archive_build': True,
                        'gs_bucket': 'gs://chromium-browser-snapshots'}))

B('Linux x64', 'linux64_full', 'compile|testers', 'chromium')
F('linux64_full', linux().ChromiumFactory(
    clobber=True,
    factory_properties={
        'archive_build': True,
        'gs_bucket': 'gs://chromium-browser-snapshots',
        'gclient_env': {'GYP_DEFINES':'target_arch=x64'}}))

def Update(config, active_master, c):
  return helper.Update(c)
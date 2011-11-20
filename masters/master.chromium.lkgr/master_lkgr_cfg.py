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

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')
def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')
def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')

defaults['category'] = '1lkgr'

# Global scheduler
S('chromium_lkgr', branch='src', treeStableTimer=1, categories=['lkgr'])

################################################################################
## Windows
################################################################################

B('Win', 'win_full', 'compile|windows', 'chromium_lkgr')
F('win_full', win().ChromiumFactory(
    clobber=True,
    project='all.sln',
    factory_properties={'archive_build': True,
                        'extra_archive_paths': 'chrome_frame',
                        'gs_bucket': 'gs://chromium-browser-continuous',}))

################################################################################
## Mac
################################################################################

B('Mac', 'mac_full', 'compile|testers', 'chromium_lkgr')
F('mac_full', mac().ChromiumFactory(
    clobber=True,
    factory_properties={'archive_build': True,
                        'gs_bucket': 'gs://chromium-browser-continuous'}))

################################################################################
## Linux
################################################################################

B('Linux', 'linux_full', 'compile|testers', 'chromium_lkgr')
F('linux_full', linux().ChromiumFactory(
    clobber=True,
    factory_properties={'archive_build': True,
                        'gs_bucket': 'gs://chromium-browser-continuous'}))

B('Linux x64', 'linux64_full', 'compile|testers', 'chromium_lkgr')
F('linux64_full', linux().ChromiumFactory(
    clobber=True,
    factory_properties={
        'archive_build': True,
        'gs_bucket': 'gs://chromium-browser-continuous',
        'gclient_env': {'GYP_DEFINES':'target_arch=x64'}}))

B('ASAN Release', 'linux_asan_rel', 'compile', 'chromium_lkgr')
F('linux_asan_rel', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=asan', 'chrome', 'DumpRenderTree'],
    factory_properties={
       'asan_archive_build': True,
       'gs_bucket': 'gs://chromium-browser-asan',
       'gclient_env': {'GYP_DEFINES': 'asan=1 linux_use_tcmalloc=0 '}}))

B('ASAN Debug', 'linux_asan_dbg', 'compile', 'chromium_lkgr')
F('linux_asan_dbg', linux().ChromiumASANFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=asan', 'chrome', 'DumpRenderTree'],
    factory_properties={
       'asan_archive_build': True,
       'gs_bucket': 'gs://chromium-browser-asan',
       'gclient_env': {'GYP_DEFINES': 'asan=1 linux_use_tcmalloc=0 '}}))


def Update(config, active_master, c):
  return helper.Update(c)

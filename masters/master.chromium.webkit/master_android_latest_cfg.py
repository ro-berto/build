# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def linux_android(): return chromium_factory.ChromiumFactory('',
    'linux2', nohooks_on_update=True, target_os='android')


################################################################################
## Release
################################################################################

defaults['category'] = '9android latest'

#
# Android scheduler
#
S('s9_android_webkit', branch='trunk', treeStableTimer=60)

#
# Triggerable scheduler for the builder
#
T('android_trigger')

chromium_android_archive = master_config.GetGSUtilUrl(
    'chromium-android', 'webkit_latest_dbg')
#
# Linux Rel Builder
#
B('Android Builder', 'f_android_rel', auto_reboot=True,
  scheduler='s9_android_webkit')
F('f_android_rel', linux_android().ChromiumWebkitLatestAnnotationFactory(
    annotation_script='src/build/android/buildbot/bb_webkit_latest_builder.sh'))

B('Android Builder (dbg)', 'f_android_dbg', auto_reboot=True,
  scheduler='s9_android_webkit')
F('f_android_dbg', linux_android().ChromiumWebkitLatestAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_webkit_latest_builder.sh',
    factory_properties={
        'trigger': 'android_trigger',
        'build_url': chromium_android_archive,
        }))

B('Android Tests (dbg)', 'f_android_dbg_tests', None, 'android_trigger',
  auto_reboot=False)
F('f_android_dbg_tests', linux_android().ChromiumWebkitLatestAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_webkit_latest_tester.sh',
    factory_properties={'build_url': chromium_android_archive}))

def Update(config, active_master, c):
  return helper.Update(c)

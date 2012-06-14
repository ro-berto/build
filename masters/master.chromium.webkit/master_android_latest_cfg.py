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

def linux_android(): return chromium_factory.ChromiumFactory('',
    'linux2', nohooks_on_update=True, target_os='android')


################################################################################
## Release
################################################################################

defaults['category'] = '9android latest'

#
# Main release scheduler for webkit
#
S('s9_android_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Linux Rel Builder
#
B('Android Builder', 'f_android_rel', auto_reboot=True,
  scheduler='s9_android_webkit_rel')
F('f_android_rel', linux_android().ChromiumWebkitLatestAnnotationFactory(
    annotation_script='src/build/android/buildbot_webkit_main.sh'))

def Update(config, active_master, c):
  return helper.Update(c)

# Copyright (c) 2012 The Chromium Authors. All rights reserved.
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

def linux_android(): return chromium_factory.ChromiumFactory(
    '', 'linux2', nohooks_on_update=True, target_os='android')

defaults['category'] = '5android'

#
# Main release scheduler for src/
#
S('android', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the builder
#
T('android_trigger')

#
# Android Builder
#
B('Android Builder', 'rel', 'android', 'android', notify_on_missing=True)
F('rel', linux_android().ChromiumAnnotationFactory(
    target='Release',
    annotation_script='src/build/android/buildbot_main.sh',
    factory_properties={'trigger': 'android_trigger'}))


def Update(config_arg, active_master, c):
  return helper.Update(c)

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

chromium_android_archive = master_config.GetArchiveUrl(
    None, None, 'Chromium_Android_Builder__dbg_', 'linux',
    static_host='master.chromium.org:8803')

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
B('Chromium Android Builder (dbg)', 'f_android_dbg', 'android', 'android',
  notify_on_missing=True)
F('f_android_dbg', linux_android().ChromiumAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_main_builder.sh',
    factory_properties={'trigger': 'android_trigger'}))

B('Chromium Android Tester (dbg)', 'f_android_dbg_tests', None,
  'android_trigger', notify_on_missing=True)
F('f_android_dbg_tests', linux_android().ChromiumAnnotationFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_main_tester.sh',
    factory_properties={'build_url': chromium_android_archive}))


def Update(config_arg, active_master, c):
  return helper.Update(c)

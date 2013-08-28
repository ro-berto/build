# Copyright 2013 The Chromium Authors. All rights reserved.
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


def android():
  return chromium_factory.ChromiumFactory('', 'linux2', nohooks_on_update=True,
                                          target_os='android')

defaults['category'] = 'android'

android_dbg_archive = master_config.GetGSUtilUrl('chromium-webrtc',
                                                 'android_dbg')
android_rel_archive = master_config.GetGSUtilUrl('chromium-webrtc',
                                                 'android_rel')

scheduler = 'webrtc_android_scheduler'
S(scheduler, branch='trunk', treeStableTimer=0)

T('android_trigger_dbg')
T('android_trigger_rel')

B('Android Builder (dbg)', 'f_android_dbg', scheduler=scheduler,
  notify_on_missing=True)
F('f_android_dbg', android().ChromiumWebRTCAndroidFactory(
  target='Debug',
  annotation_script='src/build/android/buildbot/bb_run_bot.py',
  factory_properties={
      'android_bot_id': 'webrtc-builder-dbg',
      'build_url': android_dbg_archive,
      'trigger': 'android_trigger_dbg',
  }))

B('Android Tests (dbg)', 'f_android_dbg_tests', scheduler='android_trigger_dbg',
  notify_on_missing=True)
F('f_android_dbg_tests', android().ChromiumWebRTCAndroidFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'webrtc-tests-dbg',
      'build_url': android_dbg_archive,
    }))

B('Android Builder', 'f_android_rel', scheduler=scheduler,
  notify_on_missing=True)
F('f_android_rel', android().ChromiumWebRTCAndroidFactory(
  target='Release',
  annotation_script='src/build/android/buildbot/bb_run_bot.py',
  factory_properties={
      'android_bot_id': 'webrtc-builder-rel',
      'build_url': android_rel_archive,
      'trigger': 'android_trigger_rel',
  }))

B('Android Tests', 'f_android_rel_tests', scheduler='android_trigger_rel',
  notify_on_missing=True)
F('f_android_rel_tests', android().ChromiumWebRTCAndroidFactory(
    target='Release',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'webrtc-tests-rel',
      'build_url': android_rel_archive,
    }))


def Update(c):
  return helper.Update(c)

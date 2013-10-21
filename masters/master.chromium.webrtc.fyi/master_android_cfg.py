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
P = helper.Periodic


def android():
  return chromium_factory.ChromiumFactory('', 'linux2', nohooks_on_update=True,
                                          target_os='android')

S('android_webrtc_trunk_scheduler', branch='trunk', treeStableTimer=0)
S('android_webrtc_stable_scheduler', branch='stable', treeStableTimer=0)
P('android_periodic_scheduler', periodicBuildTimer=30*60)
T('android_trigger_trunk')
T('android_trigger_stable')

defaults['category'] = 'android'

android_trunk_archive = master_config.GetGSUtilUrl('chromium-webrtc',
                                                   'android_chromium_trunk')
android_stable_archive = master_config.GetGSUtilUrl('chromium-webrtc',
                                                   'android_chromium_stable')


B('Android Builder [latest WebRTC trunk]', 'android_builder_trunk_factory',
  scheduler='android_webrtc_trunk_scheduler|android_periodic_scheduler',
  notify_on_missing=True)
F('android_builder_trunk_factory', android().ChromiumWebRTCAndroidFactory(
    target='Release',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
        'android_bot_id': 'webrtc-chromium-builder-rel',
        'build_url': android_trunk_archive,
        'trigger': 'android_trigger_trunk',
    }))

B('Android Tests (JB Nexus7.2) [latest WebRTC trunk]',
  'android_tests_trunk_factory', scheduler='android_trigger_trunk',
  notify_on_missing=True)
F('android_tests_trunk_factory', android().ChromiumWebRTCAndroidFactory(
    target='Release',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'webrtc-chromium-tests-rel',
      'build_url': android_trunk_archive,
    }))

B('Android Builder [latest WebRTC stable]', 'android_builder_stable_factory',
  scheduler='android_webrtc_stable_scheduler|android_periodic_scheduler',
  notify_on_missing=True)
F('android_builder_stable_factory', android().ChromiumWebRTCAndroidFactory(
    target='Release',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
        'android_bot_id': 'webrtc-chromium-builder-rel',
        'build_url': android_stable_archive,
        'trigger': 'android_trigger_stable',
    }))

B('Android Tests (JB Nexus7.2) [latest WebRTC stable]',
  'android_tests_stable_factory', scheduler='android_trigger_stable',
  notify_on_missing=True)
F('android_tests_stable_factory', android().ChromiumWebRTCAndroidFactory(
    target='Release',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'webrtc-chromium-tests-rel',
      'build_url': android_stable_archive,
    }))


def Update(config, active_master, c):
  helper.Update(c)


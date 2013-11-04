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

S('android_webrtc_scheduler', branch='trunk', treeStableTimer=0)
P('android_periodic_scheduler', periodicBuildTimer=30*60)
T('android_trigger')

defaults['category'] = 'android'

android_archive = master_config.GetGSUtilUrl('chromium-webrtc',
                                             'android_chromium_trunk')


B('Android Builder [latest WebRTC+libjingle]', 'android_builder_factory',
  scheduler='android_webrtc_scheduler|android_periodic_scheduler',
  notify_on_missing=True)
F('android_builder_factory', android().ChromiumWebRTCAndroidFactory(
    target='Release',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
        'android_bot_id': 'webrtc-chromium-builder-rel',
        'build_url': android_archive,
        'trigger': 'android_trigger',
    }))

B('Android Tests (JB Nexus7.2) [latest WebRTC+libjingle]',
  'android_tests_factory', scheduler='android_trigger',
  notify_on_missing=True)
F('android_tests_factory', android().ChromiumWebRTCAndroidFactory(
    target='Release',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'webrtc-chromium-tests-rel',
      'build_url': android_archive,
    }))


def Update(config, active_master, c):
  helper.Update(c)


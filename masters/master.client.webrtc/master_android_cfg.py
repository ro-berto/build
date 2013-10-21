# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory
from master.factory import webrtc_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable


def android_apk():
  return chromium_factory.ChromiumFactory('', 'linux2', nohooks_on_update=True,
                                          target_os='android')
def android_webrtc():
  return webrtc_factory.WebRTCFactory('', 'linux2', nohooks_on_update=True,
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


def f_dbg_android_tests(bot_id_suffix):
  return android_apk().ChromiumWebRTCAndroidFactory(
    target='Debug',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'webrtc-native-tests-dbg-%s' % bot_id_suffix,
      'build_url': android_dbg_archive,
    })


def f_rel_android_tests(bot_id_suffix):
  return android_apk().ChromiumWebRTCAndroidFactory(
    target='Release',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
      'android_bot_id': 'webrtc-native-tests-rel-%s' % bot_id_suffix,
      'build_url': android_rel_archive,
    })

# WebRTC standalone builders (no tests).
B('Android (dbg)', 'f_android_dbg', scheduler=scheduler,
  notify_on_missing=True)
F('f_android_dbg', android_webrtc().ChromiumAnnotationFactory(
  target='Debug',
  annotation_script='src/build/android/buildbot/bb_run_bot.py',
  factory_properties={
      'android_bot_id': 'webrtc-main-clobber',
  }))

B('Android', 'f_android_rel', scheduler=scheduler,
  notify_on_missing=True)
F('f_android_rel', android_webrtc().ChromiumAnnotationFactory(
  target='Release',
  annotation_script='src/build/android/buildbot/bb_run_bot.py',
  factory_properties={
      'android_bot_id': 'webrtc-main-clobber',
  }))

# WebRTC native test APKs: builders.
B('Android Chromium-APK Builder (dbg)', 'f_android_apk_dbg',
  scheduler=scheduler, notify_on_missing=True)
F('f_android_apk_dbg', android_apk().ChromiumWebRTCAndroidFactory(
  target='Debug',
  annotation_script='src/build/android/buildbot/bb_run_bot.py',
  factory_properties={
      'android_bot_id': 'webrtc-native-builder-dbg',
      'build_url': android_dbg_archive,
      'trigger': 'android_trigger_dbg',
  }))

B('Android Chromium-APK Builder', 'f_android_apk_rel', scheduler=scheduler,
  notify_on_missing=True)
F('f_android_apk_rel', android_apk().ChromiumWebRTCAndroidFactory(
  target='Release',
  annotation_script='src/build/android/buildbot/bb_run_bot.py',
  factory_properties={
      'android_bot_id': 'webrtc-native-builder-rel',
      'build_url': android_rel_archive,
      'trigger': 'android_trigger_rel',
  }))

# WebRTC native test APKs: device testers.
B('Android Chromium-APK Tests (ICS GalaxyNexus)(dbg)',
  'f_android_ics_galaxynexus_dbg_tests', scheduler='android_trigger_dbg',
  notify_on_missing=True)
F('f_android_ics_galaxynexus_dbg_tests', f_dbg_android_tests('ics-gn'))

B('Android Chromium-APK Tests (JB Nexus7.2)(dbg)',
  'f_android_jb_nexus7.2_dbg_tests', scheduler='android_trigger_dbg',
  notify_on_missing=True)
F('f_android_jb_nexus7.2_dbg_tests', f_dbg_android_tests('jb-n72'))

B('Android Chromium-APK Tests (ICS GalaxyNexus)',
  'f_android_ics_galaxynexus_rel_tests', scheduler='android_trigger_rel',
  notify_on_missing=True)
F('f_android_ics_galaxynexus_rel_tests', f_rel_android_tests('ics-gn'))

B('Android Chromium-APK Tests (JB Nexus7.2)',
  'f_android_jb_nexus7.2_rel_tests', scheduler='android_trigger_rel',
  notify_on_missing=True)
F('f_android_jb_nexus7.2_rel_tests', f_rel_android_tests('jb-n72'))


def Update(c):
  return helper.Update(c)

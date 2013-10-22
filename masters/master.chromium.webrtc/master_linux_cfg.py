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
P = helper.Periodic
T = helper.Triggerable


def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')

S('linux_rel_scheduler', branch='src', treeStableTimer=60)
P('linux_daily_scheduler', periodicBuildTimer=24*60*60)
T('linux_rel_trigger')

chromium_rel_archive = master_config.GetGSUtilUrl('chromium-webrtc',
                                                  'Linux Builder')
tests = [
    'webrtc_manual_browser_tests',
    # 'webrtc_manual_content_browsertests',  Disabled: crbug.com/281492.
    # 'webrtc_content_unittests',  # Disabled: crbug.com/310115.
    # 'webrtc_perf_content_unittests',  # Disabled: crbug.com/310115.
]

defaults['category'] = 'linux'

B('Linux Builder', 'linux_rel_factory', scheduler='linux_rel_scheduler',
  notify_on_missing=True)
F('linux_rel_factory', linux().ChromiumWebRTCFactory(
    slave_type='Builder',
    target='Release',
    options=['--compiler=goma', '--build-tool=ninja', '--',
             'chromium_builder_webrtc'],
    factory_properties={
        'trigger': 'linux_rel_trigger',
        'build_url': chromium_rel_archive,
    }))

B('Linux Tester', 'linux_tester_factory', scheduler='linux_rel_trigger')
F('linux_tester_factory', linux().ChromiumWebRTCFactory(
    slave_type='Tester',
    build_url=chromium_rel_archive,
    tests=tests,
    factory_properties={
        'virtual_webcam': True,
        'use_xvfb_on_linux': True,
        'show_perf_results': True,
        'halt_on_missing_build': True,
        'perf_id': 'chromium-webrtc-rel-linux',
    }))

# Builder to catch errors when enable_webrtc=0.
B('Linux Daily WebRTC Disabled', 'linux_webrtc_disabled_factory',
  scheduler='linux_daily_scheduler')
F('linux_webrtc_disabled_factory', linux().ChromiumWebRTCFactory(
    slave_type='BuilderTester',
    factory_properties={
        'gclient_env': {'GYP_DEFINES': ('enable_webrtc=0 '
                                        'component=static_library')},
    }))

def Update(config, active_master, c):
  helper.Update(c)

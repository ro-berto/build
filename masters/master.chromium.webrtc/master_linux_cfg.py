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


def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')
def linux_tester():
  return chromium_factory.ChromiumFactory('src/out', 'linux2',
                                          nohooks_on_update=True)

S('linux_rel_scheduler', branch='src', treeStableTimer=60)
T('linux_rel_trigger')

chromium_rel_archive = master_config.GetGSUtilUrl('chromium-webrtc',
                                                  'Linux Builder')
tests = ['pyauto_webrtc_tests']

defaults['category'] = 'linux'

B('Linux Builder', 'linux_rel_factory', scheduler='linux_rel_scheduler',
  notify_on_missing=True)
F('linux_rel_factory', linux().ChromiumFactory(
    slave_type='Builder',
    target='Release',
    options=['--compiler=goma', 'chromium_builder_webrtc'],
    factory_properties={
        'trigger': 'linux_rel_trigger',
        'build_url': chromium_rel_archive,
    }))

B('Linux Tester', 'linux_tester_factory', scheduler='linux_rel_trigger')
F('linux_tester_factory', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=chromium_rel_archive,
    tests=tests,
    factory_properties={
        'pyauto_env': {'DO_NOT_RESTART_PYTHON_FOR_PYAUTO': '1'},
        'use_xvfb_on_linux': True,
        'show_perf_results': True,
        'halt_on_missing_build': True,
        'perf_id': 'chromium-webrtc-rel-linux',
    }))

def Update(config, active_master, c):
  helper.Update(c)

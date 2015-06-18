# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='chromium_local',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[
          'Linux ChromiumOS Full',
          'Linux ChromiumOS Builder',
          'Linux ChromiumOS Ozone Builder',
          'Linux ChromiumOS Builder (dbg)',
          'Linux ChromiumOS GN',
          'Linux ChromiumOS GN (dbg)',
      ]),
      Triggerable(name='chromiumos_rel_trigger', builderNames=[
          'Linux ChromiumOS Tests (1)',
      ]),
      Triggerable(name='chromiumos_rel_ozone_trigger', builderNames=[
          'Linux ChromiumOS Ozone Tests (1)',
      ]),
      Triggerable(name='chromiumos_dbg_trigger', builderNames=[
          'Linux ChromiumOS Tests (dbg)(1)',
      ]),
  ])
  c['builders'].extend([
      {
        'name': spec['buildername'],
        'factory': m_annotator.BaseFactory('chromium',
                                           triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': '1linux',
      } for spec in [
          # Linux ChromiumOS
          {'buildername': 'Linux ChromiumOS Full'},
          {'buildername': 'Linux ChromiumOS Builder',
           'triggers': ['chromiumos_rel_trigger']},
          {'buildername': 'Linux ChromiumOS Tests (1)'},

          # Linux ChromiumOS GN
          {'buildername': 'Linux ChromiumOS GN'},
          {'buildername': 'Linux ChromiumOS GN (dbg)'},

          # Linux ChromiumOS Ozone
          {'buildername': 'Linux ChromiumOS Ozone Builder',
           'triggers': ['chromiumos_rel_ozone_trigger']},
          {'buildername': 'Linux ChromiumOS Ozone Tests (1)'},

          # Linux ChromiumOS (dbg)
          {'buildername': 'Linux ChromiumOS Builder (dbg)',
           'triggers': ['chromiumos_dbg_trigger']},
          {'buildername': 'Linux ChromiumOS Tests (dbg)(1)'},
      ]
  ])

# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='win_src',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[
          'Win Builder',
          'Win x64 Builder',
          'Win x64 Builder (dbg)',
          'Win Builder (dbg)',
          'Win x64 GN',
          'Win x64 GN (dbg)',
          'Win8 GN (dbg)',
      ]),
      Triggerable(name='win_rel_trigger', builderNames=[
          'XP Tests (1)',
          'Vista Tests (1)',
          'Win7 Tests (1)',
      ]),
      Triggerable(name='win_x64_rel_trigger', builderNames=[
          'Win 7 Tests x64 (1)',
      ]),
      Triggerable(name='win_dbg_trigger', builderNames=[
          'Win7 Tests (dbg)(1)',
          'Win8 Aura',
      ]),
  ])
  specs = [
    {
      'name': 'Win Builder',
      'triggers': ['win_rel_trigger'],
    },
    {'name': 'XP Tests (1)'},
    {'name': 'Vista Tests (1)'},
    {'name': 'Win7 Tests (1)'},
    {
      'name': 'Win x64 Builder',
      'triggers': ['win_x64_rel_trigger'],
    },
    {'name': 'Win 7 Tests x64 (1)'},
    {'name': 'Win x64 Builder (dbg)'},
    {
      'name': 'Win Builder (dbg)',
      'triggers': ['win_dbg_trigger'],
    },
    {'name': 'Win7 Tests (dbg)(1)'},
    {'name': 'Win8 Aura'},
    {'name': 'Win x64 GN', 'timeout': 3600},
    {'name': 'Win x64 GN (dbg)'},
    {'name': 'Win8 GN (dbg)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            spec.get('recipe', 'chromium'),
            factory_properties=spec.get('factory_properties'),
            triggers=spec.get('triggers'),
            timeout=spec.get('timeout', 2400)),
        'notify_on_missing': True,
        'category': '2windows',
      } for spec in specs
  ])

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
          'Win8 GYP (dbg)',
          'WinClang64 (dbg)',
          'Win8 GYP',
      ]),
  ])
  specs = [
    {'name': 'Win Builder'},
    {'name': 'Win7 (32) Tests'},
    {'name': 'Win7 Tests (1)'},
    {'name': 'Win x64 Builder'},
    {'name': 'Win 7 Tests x64 (1)'},
    {'name': 'Win x64 Builder (dbg)'},
    {'name': 'Win Builder (dbg)'},
    {'name': 'Win7 Tests (dbg)(1)'},
    {'name': 'Win8 GYP'},
    {'name': 'Win8 GYP (dbg)'},
    {'name': 'WinClang64 (dbg)'},
    {'name': 'Win10 Tests x64'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            spec.get('recipe', 'chromium'),
            factory_properties=spec.get('factory_properties'),
            timeout=spec.get('timeout', 2400)),
        'notify_on_missing': True,
        'category': '2windows',
      } for spec in specs
  ])

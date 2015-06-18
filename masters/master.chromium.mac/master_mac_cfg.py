# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='mac_src',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[
          'Mac Builder',
          'Mac Builder (dbg)',
          'Mac GN',
          'Mac GN (dbg)',
      ]),
      Triggerable(name='mac_rel_trigger', builderNames=[
          'Mac10.6 Tests',
          'Mac10.8 Tests',
          'Mac10.9 Tests',
          'Mac10.10 Tests',
      ]),
      Triggerable(name='mac_dbg_trigger', builderNames=[
          'Mac10.9 Tests (dbg)',
      ]),
  ])
  specs = [
    {
      'name': 'Mac Builder',
      'triggers': ['mac_rel_trigger'],
    },
    {'name': 'Mac10.6 Tests'},
    {'name': 'Mac10.8 Tests'},
    {'name': 'Mac10.9 Tests'},
    {'name': 'Mac10.10 Tests'},
    {
      'name': 'Mac Builder (dbg)',
      'triggers': ['mac_dbg_trigger'],
    },
    {'name': 'Mac10.9 Tests (dbg)'},
    {'name': 'Mac GN'},
    {'name': 'Mac GN (dbg)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            spec.get('recipe', 'chromium'),
            factory_properties=spec.get('factory_properties'),
            triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': '3mac',
      } for spec in specs
  ])

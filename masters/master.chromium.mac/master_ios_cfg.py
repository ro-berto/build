# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='ios',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[
          'ios-device',
          'ios-simulator',
      ]),
  ])
  specs = [
    {'name': 'ios-device'},
    {'name': 'ios-simulator'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            'ios/unified_builder_tester',
            factory_properties=spec.get('factory_properties')),
        'notify_on_missing': True,
        'category': '3mac',
      } for spec in specs
  ])

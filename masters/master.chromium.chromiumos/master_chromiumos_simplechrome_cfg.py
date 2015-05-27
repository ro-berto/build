# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.factory import annotator_factory

from buildbot.schedulers.basic import SingleBranchScheduler

m_annotator = annotator_factory.AnnotatorFactory()

builders = [{
  'name': 'ChromiumOS %s Compile' % (board,),
  'factory': m_annotator.BaseFactory('chromium'),
  'notify_on_missing': True,
  'category': '4simplechrome',
} for board in ('x86-generic', 'amd64-generic', 'daisy')]


def Update(_config, active_master, c):
  c['schedulers'].append(SingleBranchScheduler(
      name='chromium_simplechrome',
      branch='master',
      treeStableTimer=60,
      builderNames=[b['name'] for b in builders]
  ))
  c['builders'] += builders

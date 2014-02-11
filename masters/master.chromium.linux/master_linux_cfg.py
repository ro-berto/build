# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(_config, _active_master, c):
  c['schedulers'].extend([
      Triggerable(name='linux_rel_trigger', builderNames=[
          'Linux Tests',
          'Linux Sync',
      ]),
      Triggerable(name='linux_gtk_trigger', builderNames=[
          'Linux GTK Tests',
      ]),
      Triggerable(name='linux_dbg_32_trigger', builderNames=[
          'Linux Tests (dbg)(1)(32)',
          'Linux Tests (dbg)(2)(32)',
      ]),
      Triggerable(name='linux_dbg_trigger', builderNames=[
          'Linux Tests (dbg)(1)',
          'Linux Tests (dbg)(2)',
      ]),
  ])
  c['builders'].extend([
      {
        'name': spec['buildername'],
        'factory': m_annotator.BaseFactory('chromium',
                                           triggers=spec.get('triggers')),
        'notify_on_missing': True,
      } for spec in [
          {'buildername': 'Linux Builder',
           'triggers': ['linux_rel_trigger']},
          {'buildername': 'Linux Tests'},
          {'buildername': 'Linux Sync'},
          {'buildername': 'Linux GTK Builder',
           'triggers': ['linux_gtk_trigger']},
          {'buildername': 'Linux GTK Tests'},
          {'buildername': 'Linux Builder (dbg)(32)',
           'triggers': ['linux_dbg_32_trigger']},
          {'buildername': 'Linux Tests (dbg)(1)(32)'},
          {'buildername': 'Linux Tests (dbg)(2)(32)'},
          {'buildername': 'Linux Builder (dbg)',
           'triggers': ['linux_dbg_trigger']},
          {'buildername': 'Linux Tests (dbg)(1)'},
          {'buildername': 'Linux Tests (dbg)(2)'},
          {'buildername': 'Linux Clang (dbg)'},
      ]
  ])

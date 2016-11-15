# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties
from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master import master_utils
from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumLinux


revision_getter = master_utils.ConditionalProperty(
    lambda build: build.getProperty('revision'),
    WithProperties('%(revision)s'),
    'master')

def m_remote_run_chromium_src(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/src.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      use_gitiles=True,
      **kwargs)


def Update(_config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='linux_src',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[
          'Linux Builder',
          'Linux Builder (dbg)(32)',
          'Linux Builder (dbg)',
          'Cast Linux',
          'Blimp Linux (dbg)',
          # Trusty
          # TODO(yyanagisawa): rename Blimp Linux to Blimp Linux Trusty?
          # This change adds builders for trusty but Blimp is already using
          # trusty.
          'Linux Builder Trusty',
          'Linux Builder Trusty (dbg)(32)',
          'Linux Builder Trusty (dbg)',
          'Cast Linux Trusty',
      ]),
  ])
  specs = [
    {'name': 'Linux Builder'},
    {'name': 'Linux Tests'},
    {'name': 'Linux Builder (dbg)(32)'},
    {'name': 'Linux Tests (dbg)(1)(32)'},
    {'name': 'Linux Builder (dbg)'},
    {'name': 'Linux Tests (dbg)(1)'},
    {'name': 'Cast Linux'},
    {'name': 'Blimp Linux (dbg)'},
    # Trusty
    {'name': 'Linux Builder Trusty'},
    {'name': 'Linux Tests Trusty'},
    {'name': 'Linux Tests Trusty (dbg)(1)(32)'},
    {'name': 'Linux Builder Trusty (dbg)'},
    {'name': 'Linux Builder Trusty (dbg)(32)'},
    {'name': 'Linux Tests Trusty (dbg)(1)'},
    {'name': 'Cast Linux Trusty'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run_chromium_src('chromium'),
        'notify_on_missing': True,
        'category': '4linux',
      } for spec in specs
  ])

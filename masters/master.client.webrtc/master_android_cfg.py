# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.WebRTC


def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)


def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_android_scheduler',
                            branch='master',
                            treeStableTimer=30,
                            builderNames=[
          'Android32 (M Nexus5X)(dbg)',
          'Android32 (M Nexus5X)',
          'Android64 (M Nexus5X)(dbg)',
          'Android64 (M Nexus5X)',
          'Android32 Builder x86',
          'Android32 Builder x86 (dbg)',
          'Android64 Builder x64 (dbg)',
          'Android32 (more configs)',
      ]),
  ])

  # 'slavebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple slave machines.
  specs = [
    {'name': 'Android32 (M Nexus5X)(dbg)', 'slavebuilddir': 'android_arm32'},
    {'name': 'Android32 (M Nexus5X)', 'slavebuilddir': 'android_arm32'},
    {'name': 'Android64 (M Nexus5X)(dbg)', 'slavebuilddir': 'android_arm64'},
    {'name': 'Android64 (M Nexus5X)', 'slavebuilddir': 'android_arm64'},
    {'name': 'Android32 Builder x86', 'slavebuilddir': 'android_x86'},
    {'name': 'Android32 Builder x86 (dbg)', 'slavebuilddir': 'android_x86'},
    {'name': 'Android64 Builder x64 (dbg)', 'slavebuilddir': 'android_x64'},
    {
      'name': 'Android32 (more configs)',
      'recipe': 'webrtc/more_configs',
      'slavebuilddir': 'android',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run(spec['recipe']) if 'recipe' in spec
                   else m_remote_run('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'android',
        'slavebuilddir': spec.get('slavebuilddir', 'android'),
      } for spec in specs
  ])

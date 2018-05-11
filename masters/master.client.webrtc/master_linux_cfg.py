# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory
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


m_annotator = annotator_factory.AnnotatorFactory()


def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_linux_scheduler',
                            branch='master',
                            treeStableTimer=30,
                            builderNames=[
          'Linux32 Debug',
          'Linux32 Release',
          'Linux64 Debug',
          'Linux64 Release',
          'Linux32 Debug (ARM)',
          'Linux32 Release (ARM)',
          'Linux64 Debug (ARM)',
          'Linux64 Release (ARM)',
          'Linux64 Release (GCC)',
          'Linux Asan',
          'Linux MSan',
          'Linux Tsan v2',
          'Linux UBSan',
          'Linux UBSan vptr',
          'Linux (more configs)',
          'Linux64 Release (Libfuzzer)',
      ]),
  ])

  # 'slavebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple slave machines.
  specs = [
    {'name': 'Linux32 Debug (ARM)', 'slavebuilddir': 'linux_arm'},
    {'name': 'Linux32 Release (ARM)', 'slavebuilddir': 'linux_arm'},
    {'name': 'Linux32 Debug', 'slavebuilddir': 'linux32'},
    {'name': 'Linux32 Release', 'slavebuilddir': 'linux32'},
    {'name': 'Linux64 Debug', 'slavebuilddir': 'linux64'},
    {'name': 'Linux64 Release', 'slavebuilddir': 'linux64'},
    {'name': 'Linux64 Debug (ARM)', 'slavebuilddir': 'linux_arm64'},
    {'name': 'Linux64 Release (ARM)', 'slavebuilddir': 'linux_arm64'},
    {'name': 'Linux64 Release (GCC)', 'slavebuilddir': 'linux_gcc'},
    {'name': 'Linux Asan', 'slavebuilddir': 'linux_asan'},
    {'name': 'Linux MSan', 'slavebuilddir': 'linux_msan'},
    {'name': 'Linux Tsan v2', 'slavebuilddir': 'linux_tsan2'},
    {'name': 'Linux UBSan', 'slavebuilddir': 'linux_ubsan'},
    {'name': 'Linux UBSan vptr', 'slavebuilddir': 'linux_ubsan_vptr'},
    {
      'name': 'Linux (more configs)',
      'recipe': 'webrtc/more_configs',
      'slavebuilddir': 'linux64',
    },
    {
      'name': 'Linux64 Release (Libfuzzer)',
      'recipe': 'webrtc/libfuzzer',
      'slavebuilddir': 'linux64_libfuzzer',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run(spec['recipe']) if 'recipe' in spec
                   else m_remote_run('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'linux',
        'slavebuilddir': spec['slavebuilddir'],
      } for spec in specs
  ])

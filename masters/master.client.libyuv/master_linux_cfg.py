# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='libyuv_linux_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=[
          'Linux32 Debug',
          'Linux32 Release',
          'Linux64 Debug',
          'Linux64 Release',
          'Linux64 Debug (GYP)',
          'Linux64 Release (GYP)',
          # TODO(kjellander): Add when trybot is green (crbug.com/625889).
          #'Linux GCC',
          'Linux Asan',
          'Linux Memcheck',
          'Linux MSan',
          'Linux Tsan v2',
          'Linux UBSan',
          'Linux UBSan vptr',
      ]),
  ])

  specs = [
    {'name': 'Linux32 Debug', 'slavebuilddir': 'linux32'},
    {'name': 'Linux32 Release', 'slavebuilddir': 'linux32'},
    {'name': 'Linux64 Debug', 'slavebuilddir': 'linux64'},
    {'name': 'Linux64 Release', 'slavebuilddir': 'linux64'},
    {'name': 'Linux64 Debug (GYP)', 'slavebuilddir': 'linux64_gyp'},
    {'name': 'Linux64 Release (GYP)', 'slavebuilddir': 'linux64_gyp'},
    # TODO(kjellander): Add when trybot is green (crbug.com/625889).
    #{'name': 'Linux GCC', 'slavebuilddir': 'linux_gcc'},
    {'name': 'Linux Asan', 'slavebuilddir': 'linux_asan'},
    {'name': 'Linux Memcheck', 'slavebuilddir': 'linux_memcheck_tsan'},
    {'name': 'Linux MSan', 'slavebuilddir': 'linux_msan'},
    {'name': 'Linux Tsan v2', 'slavebuilddir': 'linux_tsan2'},
    {'name': 'Linux UBSan', 'slavebuilddir': 'linux_ubsan'},
    {'name': 'Linux UBSan vptr', 'slavebuilddir': 'linux_ubsan_vptr'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('libyuv/libyuv'),
        'notify_on_missing': True,
        'category': 'linux',
        'slavebuilddir': spec['slavebuilddir'],
      } for spec in specs
  ])

# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties
from buildbot.scheduler import Scheduler
from buildbot.scheduler import Triggerable

from master import master_utils
from master.factory import remote_run_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumMemory

def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)

def Update(_config, active_master, c):
  c['schedulers'].extend([
      Scheduler(name='linux_memory_rel',
                branch='master',
                treeStableTimer=60,
                builderNames=[
          'Android CFI',
          'Linux ASan LSan Builder',
          'Linux CFI',
          'Linux ChromiumOS MSan Builder',
          'Linux MSan Builder',
      ]),
      Triggerable(name='linux_asan_rel_trigger', builderNames=[
          'Linux ASan LSan Tests (1)',
          'Linux ASan Tests (sandboxed)',
      ]),
      Triggerable(name='linux_chromiumos_msan_rel_trigger',
                  builderNames=['Linux ChromiumOS MSan Tests']),
      Triggerable(name='linux_msan_rel_trigger',
                  builderNames=['Linux MSan Tests']),
  ])
  specs = [
    {
      'name': 'Android CFI',
      'category': '2android cfi',
    },
    {
      'name': 'Linux ASan LSan Builder',
      'triggers': ['linux_asan_rel_trigger'],
      'category': '1linux asan lsan msan',
    },
    {
      'name': 'Linux ASan LSan Tests (1)',
      'category': '1linux asan lsan msan',
    },
    {
      'name': 'Linux ASan Tests (sandboxed)',
      'category': '1linux asan lsan msan',
    },
    {
      'name': 'Linux CFI',
      'category': '1linux cfi',
    },
    {
      'name': 'Linux ChromiumOS MSan Builder',
      'triggers': ['linux_chromiumos_msan_rel_trigger'],
      'category': '1linux asan lsan msan',
    },
    {
      'name': 'Linux ChromiumOS MSan Tests',
      'category': '1linux asan lsan msan',
    },
    {
      'name': 'Linux MSan Builder',
      'triggers': ['linux_msan_rel_trigger'],
      'category': '1linux asan lsan msan',
    },
    {
      'name': 'Linux MSan Tests',
      'category': '1linux asan lsan msan',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run(
            'chromium', triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': spec['category'],
      } for spec in specs
  ])

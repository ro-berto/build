# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import remote_run_factory

import master_site_config
ActiveMaster = master_site_config.ChromiumMac


unified_builder_tester = remote_run_factory.RemoteRunFactory(
  active_master=ActiveMaster,
  repository='https://chromium.googlesource.com/chromium/tools/build.git',
  recipe='ios/unified_builder_tester',
  factory_properties={'path_config': 'kitchen'})


def Update(config, active_master, c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='ios',
                            branch='master',
                            treeStableTimer=60,
                            builderNames=[
          'ios-device',
          'ios-simulator-full-configs',
          'ios-device-xcode-clang',
          'ios-simulator-xcode-clang',
      ]),
  ])
  specs = [
    {'name': 'ios-device'},
    {'name': 'ios-simulator-full-configs'},
    {'name': 'ios-device-xcode-clang'},
    {'name': 'ios-simulator-xcode-clang'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': unified_builder_tester,
        'notify_on_missing': True,
        'category': '3mac',
      } for spec in specs
  ])

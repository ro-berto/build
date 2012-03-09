# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the swarm master BuildFactory's.

Based on chromium_factory.py and adds chromium-specific steps."""

from master.factory import chromium_factory
from master.factory import swarm_commands

class SwarmFactory(chromium_factory.ChromiumFactory):
  def SwarmFactory(self, target='Release', clobber=False, tests=None,
                   mode=None, slave_type='BuilderTester',
                   options=None, compile_timeout=1200, build_url=None,
                   project=None, factory_properties=None, gclient_deps=None):
    factory = self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                   options, compile_timeout, build_url, project,
                                   factory_properties, gclient_deps)

    swarm_command_obj = swarm_commands.SwarmCommands(factory,
                                                     target,
                                                     self._build_dir,
                                                     self._target_platform)

    gclient_env = factory_properties.get("gclient_env")
    gyp_defines = gclient_env['GYP_DEFINES']
    if 'test_run=hashtable' in gyp_defines:
      swarm_command_obj.AddSwarmTestStep(target, self._target_platform,
          factory_properties.get('swarm_server', 'localhost'),
          factory_properties.get('swarm_port', '9001'),
          factory_properties.get('min_swarm_shards', '1'),
          factory_properties.get('max_swarm_shards', '1'),
          './src/base/base_unittest.sl')

    return factory

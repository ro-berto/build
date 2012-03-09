# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds swarm-specific commands."""

from master.factory import commands

from master.log_parser import gtest_command

class SwarmCommands(commands.FactoryCommands):
  """Encapsulates methods to add swarm commands to a buildbot factory"""

  def AddSwarmTestStep(self, target, target_platform, swarm_server, swarm_port,
                       min_shards, max_shards, manifest_file):
    script_path = self.PathJoin(self._script_dir, 'run_slavelastic.py')

    command = [self._python, script_path, '-m', min_shards, '-s', max_shards,
               '-o', target_platform, '-t', target, '-n', swarm_server,
               '-p', swarm_port, manifest_file]

    self.AddTestStep(gtest_command.GTestCommand, 'Run Tests on Swarm', command)

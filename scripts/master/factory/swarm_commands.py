# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds swarm-specific commands."""

from buildbot.process.properties import WithProperties
from buildbot.steps import shell

from master.factory import commands
from master.log_parser import gtest_command

class SwarmCommands(commands.FactoryCommands):
  """Encapsulates methods to add swarm commands to a buildbot factory"""

  def AddTriggerSwarmTestStep(self, target_platform, swarm_server,
                              min_shards, max_shards,
                              manifest_files, test_names):
    script_path = self.PathJoin(self._script_dir, 'run_slavelastic.py')

    # TODO(csharp) Merge into a single command
    for i in range(len(manifest_files)):
      swarm_request_name = WithProperties('%s-%s-' + test_names[i],
                                          'buildername:-None',
                                          'buildnumber:-None')

      command = [self._python, script_path, '-m', min_shards, '-s', max_shards,
                 '-o', target_platform, '-u', swarm_server,
                 '-t', swarm_request_name, manifest_files[i]]

      self.AddTestStep(shell.ShellCommand,
                       '%s_swarm' % test_names[i],
                       command)

  def AddGetSwarmTestStep(self, swarm_server, test_name):
    script_path = self.PathJoin(self._script_dir, 'get_swarm_results.py')

    swarm_request_name = WithProperties('%s-%s-' + test_name,
                                        'buildername:-None',
                                        'buildnumber:-None')

    command = [self._python, script_path, '-u', swarm_server,
               swarm_request_name]

    self.AddTestStep(gtest_command.GTestCommand,
                     '%s_swarm' % test_name,
                     command)

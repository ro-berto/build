# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds swarm-specific commands."""

import re

from buildbot.process.properties import WithProperties
from buildbot.steps import shell

from master.factory import commands
from master.log_parser import gtest_command


def TestStepFilterSwarm(bStep):
  """Examines the 'testfilter' property of a build and determines if this
  build has swarm steps and thus if the test should run.
  It also adds a property, swarm_tests, which contains all the tests which will
  run under swarm."""
  bStep.setProperty('swarm_tests', '')
  test_filters = bStep.build.getProperties().getProperty('testfilter')
  test_filters = test_filters or commands.DEFAULT_TESTS

  swarm_tests = ''
  for test_filter in test_filters:
    if '_swarm:' in test_filter:
      swarm_tests += test_filter.replace('_swarm:', '') + ' '
    elif test_filter.endswith('_swarm'):
      swarm_tests += test_filter[:-len('_swarm')] + ' '

  bStep.setProperty('swarm_tests', swarm_tests.strip())

  return bool(swarm_tests)


class SwarmShellForHashes(shell.ShellCommand):
  """A basic swarm ShellCommand wrapper that assumes the script it runs will
  output a list of property names and hashvalues, with each pair on its own
  line."""
  def commandComplete(self, cmd):
    shell.ShellCommand.commandComplete(self, cmd)

    re_hash_mapping = re.compile(r'^([a-z_]+) ([0-9a-f]+)')
    swarm_hashes = {}
    for line in self.stdio_log.readlines():
      match = re_hash_mapping.match(line)
      if match:
        swarm_hashes[match.group(1)] = match.group(2)

    self.setProperty('swarm_hashes', swarm_hashes)


class SwarmCommands(commands.FactoryCommands):
  """Encapsulates methods to add swarm commands to a buildbot factory"""

  def AddTriggerSwarmTestStep(self, target_platform, swarm_server, data_dir,
                              manifest_directory, tests):
    script_path = self.PathJoin(self._script_dir, 'run_slavelastic.py')

    swarm_request_name_prefix = WithProperties('%s-%s-',
                                               'buildername:-None',
                                               'buildnumber:-None')

    command = [self._python, script_path, '-o', target_platform,
               '-u', swarm_server, '-d', data_dir,
               '-t', swarm_request_name_prefix]

    # Add the tests to run, along with the minimum and maximum number of
    # shards to request.
    for test in tests:
      command.extend(['-n', self.PathJoin(manifest_directory,
                                          test.test_name + '.results'),
                      '-s', '%d' % test.shards])

    self.AddTestStep(shell.ShellCommand, 'trigger_swarm_tests', command)

  def AddGetSwarmTestStep(self, swarm_server, test_name):
    script_path = self.PathJoin(self._script_dir, 'get_swarm_results.py')

    swarm_request_name = WithProperties('%s-%s-' + test_name,
                                        'buildername:-None',
                                        'buildnumber:-None')

    command = [self._python, script_path, '-u', swarm_server,
               swarm_request_name]

    # Swarm handles the timeouts due to no ouput being produced for 10 minutes,
    # but we don't have access to the output until the whole test is done, which
    # may take more than 10 minutes, so we increase the buildbot timeout.
    timeout = 2 * 60 * 60

    self.AddTestStep(gtest_command.GTestCommand,
                     '%s_swarm' % test_name,
                     command,
                     timeout=timeout)

  def SetupWinNetworkDrive(self, drive, network_path):
    script_path = self.PathJoin(self._script_dir, 'add_network_drive.py')

    command = [self._python, script_path, '--drive', drive,
               '--network_path', network_path]

    self._factory.addStep(
        shell.ShellCommand,
        name='setup_windows_network_storage',
        description='setup_windows_network_storage',
        descriptionDone='setup_windows_network_storage',
        command=command)

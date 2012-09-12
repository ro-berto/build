# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds swarm-specific commands."""

import re

from buildbot.process.properties import Property
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
      swarm_tests += test_filter.split('_swarm:')[0] + ' '
    elif test_filter.endswith('_swarm'):
      swarm_tests += test_filter[:-len('_swarm')] + ' '

  bStep.setProperty('swarm_tests', swarm_tests.strip())

  return bool(swarm_tests)


def TestStepHasSwarmProperties(bStep):
  """Returns true if the step has the required swarm properties set."""
  properties = bStep.build.getProperties()

  try:
    properties.getProperty('testfilter')
    properties.getProperty('swarm_hashes')
  except ValueError:
    return False

  return True


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


class SwarmShellForTriggeringTests(shell.ShellCommand):
  """A simple swarm ShellCommand wrapper to ensue that all test that are sent
  to swarm and properly assigned a number of shards to run on."""
  def __init__(self, *args, **kwargs):
    self.tests = kwargs.pop('tests', [])
    self.unix_data_dir = kwargs.pop('unix_data_dir', None)
    self.windows_data_dir = kwargs.pop('windows_data_dir', None)

    shell.ShellCommand.__init__(self, *args, **kwargs)

  def start(self):
    test_filters = self.getProperty('testfilter')
    swarm_tests_hash_mapping = self.getProperty('swarm_hashes')

    command = self.command
    for test_filter in test_filters:
      if '_swarm:' in test_filter or test_filter.endswith('_swarm'):
        (test_name, _, gtest_filter) = test_filter.partition(':')
        for swarm_test in self.tests:
          if swarm_test.test_name + '_swarm' == test_name:
            command.extend(['--run_from_hash',
                            swarm_tests_hash_mapping[swarm_test.test_name],
                            swarm_test.test_name, '%d' % swarm_test.shards,
                            gtest_filter])
            continue

    # Set the hashtable directory.
    if Property('os') == 'win32':
      command.extend(['-d', self.windows_data_dir])
    else:
      command.extend(['-d', self.unix_data_dir])

    self.setCommand(command)

    shell.ShellCommand.start(self)


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
      command.extend(['--run_from_manifest',
                      self.PathJoin(manifest_directory,
                                    test.test_name + '.results'),
                      '%d' % test.shards, '*'])

    self.AddTestStep(shell.ShellCommand, 'trigger_swarm_tests', command)

  def AddTriggerSwarmTestFromTestFilterStep(self, swarm_server, unix_data_dir,
                                            windows_data_dir, tests):
    script_path = self.PathJoin(self._script_dir, 'run_slavelastic.py')

    swarm_request_name_prefix = WithProperties('%s-%s-',
                                               'buildername:-None',
                                               'buildnumber:-None')

    command = [self._python, script_path, '-o', Property('os'),
               '-u', swarm_server, '-t', swarm_request_name_prefix]

    self._factory.addStep(SwarmShellForTriggeringTests,
                          name='trigger_swarm_tests',
                          command=command,
                          unix_data_dir=unix_data_dir,
                          windows_data_dir=windows_data_dir,
                          tests=tests,
                          doStepIf=TestStepHasSwarmProperties)

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
                     timeout=timeout,
                     do_step_if=self.TestStepFilter)

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

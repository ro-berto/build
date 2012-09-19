# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds swarm-specific commands."""

from buildbot.process.properties import WithProperties
from buildbot.steps import shell

import config
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


class SwarmShellForTriggeringTests(shell.ShellCommand):
  """A simple swarm ShellCommand wrapper to ensue that all test that are sent
  to swarm and properly assigned a number of shards to run on."""
  def __init__(self, *args, **kwargs):
    self.tests = kwargs.pop('tests', [])

    shell.ShellCommand.__init__(self, *args, **kwargs)

  def start(self):
    try:
      test_filters = self.getProperty('testfilter')
    except KeyError:
      test_filters = (test.test_name + '_swarm' for test in self.tests)
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

    self.setCommand(command)

    shell.ShellCommand.start(self)


class SwarmCommands(commands.FactoryCommands):
  """Encapsulates methods to add swarm commands to a buildbot factory"""

  def AddTriggerSwarmTestStep(self, swarm_server, tests, doStepIf=True):
    script_path = self.PathJoin(self._script_dir, 'run_slavelastic.py')

    swarm_request_name_prefix = WithProperties('%s-%s-',
                                               'buildername:-None',
                                               'buildnumber:-None')

    command = [self._python, script_path, '-o', self._target_platform,
               '-u', swarm_server, '-t', swarm_request_name_prefix,
               '-d', config.Master.swarm_hashtable_server_internal]

    self._factory.addStep(
        SwarmShellForTriggeringTests,
        name='trigger_swarm_tests',
        command=command,
        tests=tests,
        doStepIf=doStepIf)

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

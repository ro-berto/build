# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds swarm-specific commands."""

from buildbot.process.properties import WithProperties
from buildbot.steps import shell
from twisted.python import log

from master import chromium_step
from master.factory import commands

from common import chromium_utils

# Indices used to get a test's name and the filter to apply to from a split
# testfilter property.
TEST_FILTER_TEST_NAME_INDEX = 0
TEST_FILTER_TEST_FILTER_INDEX = 2


def GetSwarmTests(bStep):
  """Gets the list of all the swarm tests that this step's filter
  will allow."""
  test_filters = bStep.build.getProperties().getProperty('testfilter')
  test_filters = test_filters or commands.DEFAULT_TESTS

  run_default_swarm_tests = (
      bStep.build.getProperties().getProperty('run_default_swarm_tests'))

  return commands.GetSwarmTestsFromTestFilter(test_filters,
                                              run_default_swarm_tests)


def TestStepFilterRetrieveStep(bStep):
  """Returns True if the given swarm step should be run."""
  if 'testfilter' not in bStep.build.getProperties():
    return True

  return bStep.name in GetSwarmTests(bStep)


def TestStepFilterSwarm(bStep):
  """Examines the 'testfilter' property of a build and determines if this
  build has swarm steps and thus if the test should run.
  It also adds a property, swarm_tests, which contains all the tests which will
  run under swarm."""
  swarm_tests = GetSwarmTests(bStep)
  # TODO(csharp): Keep swarm_tests as a list.
  bStep.setProperty('swarm_tests', ' '.join(swarm_tests))

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
    swarm_tests_hash_mapping = self.getProperty('swarm_hashes') or {}

    command = self.command

    # Split the test filters and remove any that aren't related to swarm.
    test_filters_split = [t.partition(':') for t in test_filters
                          if '_swarm:' in t or t.endswith('_swarm')]

    # Scan through the tests instead of the test_filter to ensure that
    # the tests are always run in the order they are listed in in
    # SWARM_TESTS.
    for swarm_test in self.tests:
      for test_filter in test_filters_split:
        if (swarm_test.test_name + '_swarm' ==
            test_filter[TEST_FILTER_TEST_NAME_INDEX]):
          if swarm_tests_hash_mapping.get(swarm_test.test_name):
            command.extend(
                [
                  '--run_from_hash',
                  swarm_tests_hash_mapping[swarm_test.test_name],
                  swarm_test.test_name,
                  '%d' % swarm_test.shards,
                  # It is necessary even if it is empty.
                  test_filter[TEST_FILTER_TEST_FILTER_INDEX],
                  ])
          else:
            log.msg('Given a swarm test, %s, that has no matching hash' %
                    swarm_test.test_name)
          break

    self.setCommand(command)

    shell.ShellCommand.start(self)


class SwarmCommands(commands.FactoryCommands):
  """Encapsulates methods to add swarm commands to a buildbot factory"""
  def __init__(self, *args, **kwargs):
    super(SwarmCommands, self).__init__(*args, **kwargs)
    self._swarm_client_dir = self.PathJoin(
        self._script_dir, '..', '..', 'third_party', 'swarm_client')

  def AddTriggerSwarmTestStep(self, swarm_server, isolation_outdir, tests,
                              doStepIf=True):
    script_path = self.PathJoin(self._swarm_client_dir, 'swarm_trigger_step.py')

    swarm_request_name_prefix = WithProperties('%s-%s-',
                                               'buildername:-None',
                                               'buildnumber:-None')

    command = [
      self._python,
      script_path,
      '-o', WithProperties('%s', 'target_os:-%s' % self._target_platform),
      '-u', swarm_server,
      '-t', swarm_request_name_prefix,
      '-d', isolation_outdir,
    ]
    assert all(i for i in command), command
    self._factory.addStep(
        SwarmShellForTriggeringTests,
        name='swarm_trigger_tests',
        description='Trigger swarm steps',
        command=command,
        tests=tests,
        doStepIf=doStepIf)

  def AddGetSwarmTestStep(self, swarm_server, test_name, num_shards):
    script_path = self.PathJoin(self._script_dir, 'get_swarm_results.py')

    swarm_request_name = WithProperties('%s-%s-' + test_name,
                                        'buildername:-None',
                                        'buildnumber:-None')

    args = ['-u', swarm_server, '-s', '%d' % num_shards, swarm_request_name]
    wrapper_args = ['--annotate=gtest', '--test-type=%s' % test_name]

    command = self.GetPythonTestCommand(script_path, arg_list=args,
                                        wrapper_args=wrapper_args)

    # Swarm handles the timeouts due to no ouput being produced for 10 minutes,
    # but we don't have access to the output until the whole test is done, which
    # may take more than 10 minutes, so we increase the buildbot timeout.
    timeout = 2 * 60 * 60

    self.AddTestStep(chromium_step.AnnotatedCommand,
                     test_name,
                     command,
                     timeout=timeout,
                     do_step_if=TestStepFilterRetrieveStep)

  def AddIsolateTest(self, test_name, using_ninja):
    if not self._target:
      log.msg('No target specified, unable to find isolated files')
      return

    isolated_directory, _ = chromium_utils.ConvertBuildDirToLegacy(
        self._build_dir, target_platform=self._target_platform,
        use_out=(using_ninja or self._target_platform.startswith('linux')))
    isolated_directory = self.PathJoin(isolated_directory, self._target)
    isolated_file = self.PathJoin(isolated_directory, test_name + '.isolated')
    script_path = self.PathJoin('src', 'tools', 'swarm_client',
                                'isolate.py')

    args = ['run', '--isolated', isolated_file, '--', '--no-cr']
    wrapper_args = ['--annotate=gtest', '--test-type=%s' % test_name]

    command = self.GetPythonTestCommand(script_path, arg_list=args,
                                        wrapper_args=wrapper_args)
    self.AddTestStep(chromium_step.AnnotatedCommand,
                     test_name,
                     command)

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

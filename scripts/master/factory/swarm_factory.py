# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the swarm master BuildFactory's.

Based on chromium_factory.py and adds chromium-specific steps."""

from master.factory import build_factory
from master.factory import chromium_factory
from master.factory import swarm_commands


class SwarmTest(object):
  """A small helper class containing any required details to run a
     swarm test.
  """
  def __init__(self, test_name, shards):
    self.test_name = test_name
    self.shards = shards


SWARM_TESTS = [
    # The test listed below must be in the REVERSE ORDER of latency to get
    # results, e.g. the slowest test should be LAST.
    #
    # The goal here is to take ~5m of actual test run per shard, e.g. the
    # 'RunTest' section in the logs, so that the trade-off of setup time
    # overhead vs latency is reasonable. The overhead is in the ~90s range, with
    # the vast majority being downloading the executable files. While it can be
    # lowered, it'll stay in the "few seconds" range due to the sheer size of
    # the executables to map.
    SwarmTest('base_unittests', 1),
    SwarmTest('net_unittests', 1),
    SwarmTest('unit_tests', 2),
    SwarmTest('interactive_ui_tests', 3),
    SwarmTest('sync_integration_tests', 4),
    SwarmTest('browser_tests', 10),
]


def SetupSwarmTests(machine, options, swarm_server, isolation_mode,
                    isolation_outdir, gyp_defines, ninja, tests):
  """This is a swarm builder."""
  # Only set the outdir if we are building the hashtable to ensure we know where
  # to load the hashtable from later.
  factory_properties = {
    'compile_env': {
      'ISOLATE_DEBUG': '1',
    },
    'data_dir': isolation_outdir,
    'gclient_env' : {
      'GYP_DEFINES': (
          'test_isolation_mode=' + isolation_mode +
          ' test_isolation_outdir=' + isolation_outdir +
          ' fastbuild=1 ' + gyp_defines
      ),
      'GYP_MSVS_VERSION': '2010',
    },
    'swarm_server': swarm_server,
    'window_manager': False,
  }
  if ninja:
    factory_properties['gclient_env']['GYP_GENERATORS'] = 'ninja'
    # Build until death.
    options = ['--build-tool=ninja'] + options + ['--', '-k', '0']

  swarm_tests = [s for s in SWARM_TESTS if s.test_name in tests]
  # Accessing machine._target_platform, this function should be a member of
  # SwarmFactory.
  # pylint: disable=W0212
  return machine.SwarmFactory(
      tests=swarm_tests,
      options=options,
      target_platform=machine._target_platform,
      factory_properties=factory_properties)


def SwarmTestBuilder(swarm_server, isolation_outdir, tests):
  """Create a basic swarm builder that runs tests via swarm."""
  f = build_factory.BuildFactory()

  # Some of the scripts require a build_dir to be set, so set it even
  # if the machine might not have it (It shouldn't matter what this is).
  build_dir = 'chrome'

  swarm_command_obj = swarm_commands.SwarmCommands(factory=f,
                                                   build_dir=build_dir)
  swarm_tests = [s for s in SWARM_TESTS if s.test_name in tests]

  # Send the swarm tests to the swarm server.
  swarm_command_obj.AddTriggerSwarmTestStep(
      swarm_server=swarm_server,
      isolation_outdir=isolation_outdir,
      tests=swarm_tests,
      doStepIf=swarm_commands.TestStepHasSwarmProperties)

  # Latency is everything, update scripts only after.
  swarm_command_obj.AddUpdateScriptStep()

  # Collect the results
  for swarm_test in swarm_tests:
    swarm_command_obj.AddGetSwarmTestStep(swarm_server, swarm_test.test_name,
                                          swarm_test.shards)

  return f


class SwarmFactory(chromium_factory.ChromiumFactory):
  def __init__(self, *args, **kwargs):
    canary = kwargs.pop('canary', False)
    super(SwarmFactory, self).__init__(*args, **kwargs)
    if canary:
      # pylint: disable=W0212
      self._solutions[0].custom_vars_list.append(('swarm_revision', ''))

  def SwarmFactory(
      self, target_platform, target='Release', clobber=False, tests=None,
      mode=None, options=None, compile_timeout=1200,
      build_url=None, project=None, factory_properties=None,
      gclient_deps=None):
    # Do not pass the tests to the ChromiumFactory, they'll be processed below.
    f = self.ChromiumFactory(target, clobber, [], mode, 'BuilderTester',
                             options, compile_timeout, build_url, project,
                             factory_properties, gclient_deps)

    swarm_command_obj = swarm_commands.SwarmCommands(
        f,
        target,
        self._build_dir,
        self._target_platform)

    gclient_env = factory_properties.get('gclient_env')
    swarm_server = factory_properties.get('swarm_server',
                                          'http://localhost:9001')
    swarm_server = swarm_server.rstrip('/')
    isolation_outdir = factory_properties.get('data_dir')
    using_ninja = '--build-tool=ninja' in (options or []),

    gyp_defines = gclient_env['GYP_DEFINES']
    if 'test_isolation_mode=hashtable' in gyp_defines:
      test_names = [test.test_name for test in tests]

      swarm_command_obj.AddGenerateResultHashesStep(
          using_ninja=using_ninja, tests=test_names, doStepIf=True)

      # Send of all the test requests as a single step.
      swarm_command_obj.AddTriggerSwarmTestStep(swarm_server, isolation_outdir,
                                                tests)

      # Each test has its output returned as its own step.
      for test in tests:
        swarm_command_obj.AddGetSwarmTestStep(swarm_server, test.test_name,
                                              test.shards)
    elif 'test_isolation_mode=check':
      for test in tests:
        swarm_command_obj.AddIsolateTest(test.test_name,
                                         using_ninja=using_ninja)

    return f

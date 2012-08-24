# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the swarm master BuildFactory's.

Based on chromium_factory.py and adds chromium-specific steps."""

from master.factory import chromium_factory
from master.factory import swarm_commands

import config

class SwarmTest(object):
  """A small helper class containing any required details to run a
     swarm test.
  """
  def __init__(self, test_name, shards):
    self.test_name = test_name
    self.shards = shards


def SetupSwarmTests(machine, data_dest_dir, data_server, options=None,
                    project=None, network_path=None, extra_gyp_defines='',
                    ninja=False):
  """This is a swarm builder."""
  factory_properties = {
    'gclient_env' : {
      'GYP_DEFINES': (
        'test_isolation_mode=hashtable '
        'test_isolation_outdir=' + data_dest_dir +
        ' ' + extra_gyp_defines +
        ' disable_nacl=1'
        ' fastbuild=1'
      ),
      'GYP_MSVS_VERSION': '2010',
    },
    'data_server': data_server,
    'data_dest_dir': data_dest_dir,
    'swarm_server': config.Master.swarm_server_internal_url
  }
  if ninja:
    factory_properties['gclient_env']['GYP_GENERATORS'] = 'ninja'
    # Build until death.
    options = ['--build-tool=ninja'] + options + ['--', '-k', '0']

  tests = [
      # They must be in the reverse order of latency to get results, e.g. the
      # slowest test should be last.
      SwarmTest('base_unittests', 1),
      SwarmTest('net_unittests', 3),
      SwarmTest('unit_tests', 4),
      SwarmTest('browser_tests', 5),
      ]

  return machine.SwarmFactory(
      tests=tests,
      options=options,
      project=project,
      factory_properties=factory_properties,
      network_path=network_path)


class SwarmFactory(chromium_factory.ChromiumFactory):
  def SwarmFactory(self, target='Release', clobber=False, tests=None,
                   mode=None, options=None, compile_timeout=1200,
                   build_url=None, project=None, factory_properties=None,
                   gclient_deps=None, network_path=None):
    # Do not pass the tests to the ChromiumFactory, they'll be processed below.
    # Set the slave_type to 'SwarmSlave' to prevent the factory from adding the
    # compile step, so we can add other steps before the compile step.
    factory = self.ChromiumFactory(target, clobber, [], mode, 'SwarmSlave',
                                   options, compile_timeout, build_url, project,
                                   factory_properties, gclient_deps)

    swarm_command_obj = swarm_commands.SwarmCommands(factory,
                                                     target,
                                                     self._build_dir,
                                                     self._target_platform)

    # Ensure the network drive is mapped on windows.
    data_dest_dir = factory_properties.get('data_dest_dir')
    if self._target_platform == 'win32':
      swarm_command_obj.SetupWinNetworkDrive(data_dest_dir[:2], network_path)

    # Now add the compile step.
    swarm_command_obj.AddCompileStep(
        project or self._project, clobber,
        mode=mode,
        options=options,
        timeout=compile_timeout,
        haltOnFailure=False)

    gclient_env = factory_properties.get('gclient_env')
    swarm_server = factory_properties.get('swarm_server',
                                          'http://localhost:9001')
    swarm_server = swarm_server.rstrip('/')

    data_server = factory_properties.get('data_server',
                                         'http://localhost:8080')
    data_server = data_server.rstrip('/')

    ninja = '--build-tool=ninja' in (options or [])

    gyp_defines = gclient_env['GYP_DEFINES']
    if 'test_isolation_mode=hashtable' in gyp_defines:
      if ninja:
        out_dir = 'out'
      elif self._target_platform == 'win32':
        out_dir = 'build'
      elif self._target_platform == 'darwin':
        out_dir = 'xcodebuild'
      else:
        out_dir = 'out'

      # Send of all the test requests as a single step.
      manifest_directory = swarm_command_obj.PathJoin('src', out_dir, target)
      hashtable_directory = swarm_command_obj.PathJoin('src', out_dir, target,
                                                       'hashtable')
      swarm_command_obj.AddTriggerSwarmTestStep(self._target_platform,
            swarm_server,
            data_server,
            hashtable_directory,
            data_dest_dir,
            manifest_directory,
            tests)

      # Each test has its output returned as its own step.
      for test in tests:
        swarm_command_obj.AddGetSwarmTestStep(swarm_server, test.test_name)

    return factory

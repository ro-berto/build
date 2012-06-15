# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the Syzygy master BuildFactory's.

Based on gclient_factory.py and adds Syzygy-specific steps."""

from master.factory import gclient_factory
from master.factory import syzygy_commands

import config


# A list of unittests to run after each build.
_UNITTESTS = [
  'agent_common_unittests',
  'block_graph_orderers_unittests',
  'block_graph_transforms_unittests',
  'block_graph_unittests',
  'common_unittests',
  'core_unittests',
  'grinder_unittests',
  'instrument_unittests',
  'parse_unittests',
  'pdb_unittests',
  'pe_orderers_unittests',
  'pe_transforms_unittests',
  'pe_unittests',
  'playback_unittests',
  'profile_unittests',
  'relink_unittests',
  'reorder_unittests',
  'rpc_service_unittests',
  'simulate_unittests',
  'wsdump_unittests',
]


class SyzygyFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the Syzygy master.cfg files."""

  def __init__(self, build_dir, target_platform=None):
    self.target_platform = target_platform
    main = gclient_factory.GClientSolution(config.Master.syzygy_url + 'trunk',
                                           name='src')

    custom_deps_list = [main]
    if config.Master.syzygy_internal_url:
      internal = gclient_factory.GClientSolution(
                     config.Master.syzygy_internal_url,
                     name='syzygy')
      custom_deps_list.append(internal)

    gclient_factory.GClientFactory.__init__(self, build_dir, custom_deps_list,
                                            target_platform=target_platform)

  def SyzygyFactory(self, target='release', clobber=False, tests=None,
                    mode=None, slave_type='BuilderTester', options=None,
                    compile_timeout=1200, build_url=None, project=None,
                    factory_properties=None, target_arch=None,
                    official_release=False):
    factory = self.BaseFactory(factory_properties=factory_properties,
                               official_release=official_release)

    syzygy_cmd_obj = syzygy_commands.SyzygyCommands(factory,
                                                    target,
                                                    self._build_dir,
                                                    self.target_platform,
                                                    target_arch)

    if official_release:
      # Compile the official_build project of the "all" solution for
      # official builds.
      syzygy_cmd_obj.AddCompileStep('../syzygy/build/all.sln;official_build')
    else:
      # Compile the build_all project of the Syzygy solution.
      syzygy_cmd_obj.AddCompileStep('../syzygy/syzygy.sln;build_all')

    # Run the unittests.
    for test_name in _UNITTESTS:
      syzygy_cmd_obj.AddAppVerifierGTestTestStep(test_name)

    if target == 'release':
      syzygy_cmd_obj.AddRandomizeChromeStep()
      syzygy_cmd_obj.AddBenchmarkChromeStep()

    if official_release:
      # Archive official build output.
      syzygy_cmd_obj.AddArchival()

    return factory

  def SyzygyCoverageFactory(self, target='release', clobber=False, tests=None,
                            mode=None, slave_type='BuilderTester', options=None,
                            compile_timeout=1200, build_url=None, project=None,
                            factory_properties=None, target_arch=None):
    """Generates the GYP solutions with "coverage=1", and performs code
    coverage reporting."""
    if not factory_properties:
      factory_properties = {}

    gclient_env = factory_properties.get('gclient_env', {})
    # Make sure gclient generates coverage-enabled projects.
    gclient_env['GYP_DEFINES'] = 'coverage=1'
    factory_properties['gclient_env'] = gclient_env

    factory = self.BaseFactory(factory_properties=factory_properties)

    syzygy_cmd_obj = syzygy_commands.SyzygyCommands(factory,
                                                    target,
                                                    self._build_dir,
                                                    self.target_platform,
                                                    target_arch)

    # Compile unittests only.
    syzygy_cmd_obj.AddCompileStep('../syzygy/syzygy.sln;build_unittests')

    # Then generate and upload a coverage report.
    syzygy_cmd_obj.AddGenerateCoverage()

    return factory

  def SyzygySmokeTestFactory(self, target=None, clobber=False, tests=None,
                             mode=None, slave_type='Tester',
                             options=None, compile_timeout=1200,
                             build_url=None, project=None,
                             factory_properties=None, target_arch=None):
    """Runs the smoke-test against the checked out version of the binaries."""
    factory = self.BaseFactory(slave_type=slave_type,
                               factory_properties=factory_properties)
    syzygy_cmd_obj = syzygy_commands.SyzygyCommands(factory,
                                                    target,
                                                    self._build_dir,
                                                    self.target_platform,
                                                    target_arch)
    syzygy_cmd_obj.AddSmokeTest()
    return factory

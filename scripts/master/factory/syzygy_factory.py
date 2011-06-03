# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the Syzygy master BuildFactory's.

Based on gclient_factory.py and adds Syzygy-specific steps."""

from master.factory import gclient_factory
from master.factory import syzygy_commands

import config


# A list of unittests to run after each build.
_UNITTESTS = [
  'call_trace_unittests',
  'core_unittests',
  'instrument_unittests',
  'pdb_unittests',
  'pe_unittests',
  'relink_unittests',
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
                    factory_properties=None, target_arch=None):
    factory = self.BaseFactory(factory_properties=factory_properties)

    syzygy_cmd_obj = syzygy_commands.SyzygyCommands(factory,
                                                    target,
                                                    self._build_dir,
                                                    self.target_platform,
                                                    target_arch)
    
    # Compile the build_all project of the Syzygy solution.
    syzygy_cmd_obj.AddCompileStep('syzygy.sln;build_all')

    # Run the unittests.
    for test_name in _UNITTESTS:
      syzygy_cmd_obj.AddBasicGTestTestStep(test_name)
    
    if target == 'release':
      syzygy_cmd_obj.AddRandomizeChromeStep()
      syzygy_cmd_obj.AddBenchmarkChromeStep()
      
    return factory

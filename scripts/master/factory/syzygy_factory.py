#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the Syzygy master BuildFactory's.

Based on gclient_factory.py and adds Syzygy-specific steps."""

from master.factory import gclient_factory
from master.factory import syzygy_commands

import config

class SyzygyFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the Syzygy master.cfg files."""

  def __init__(self, build_dir, target_platform=None):
    main = gclient_factory.GClientSolution(config.Master.syzygy_url + 'trunk',
                                           name='src',
                                           build_dir=build_dir)
    self.target_platform = target_platform

    custom_deps_list = [main]

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
    syzygy_cmd_obj.AddCompileStep('src/syzygy/syzygy.sln;build_all')

    return factory

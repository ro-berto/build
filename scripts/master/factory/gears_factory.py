#!/usr/bin/python
# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate the gears-specific BuildFactory.

Based on chromium_factory.py."""

import chromium_config as config
import chromium_commands
import chromium_factory
import gclient_factory
from master.factory import gears_commands


class GearsFactory(chromium_factory.ChromiumFactory):
  def __init__(self, build_dir, target_platform=None):
    chromium_factory.ChromiumFactory.__init__(self, build_dir, target_platform)
    gears = gclient_factory.GClientSolution(config.Master.gears_url + '/gears',
                                            'src/gears/gears')

    gears_third_party = gclient_factory.GClientSolution(
                            config.Master.gears_url + '/third_party',
                            'src/gears/third_party')

    gears_internal = gclient_factory.GClientSolution(
                         config.Master.gears_url_internal)

    self._solutions.append(gears)
    self._solutions.append(gears_third_party)
    self._solutions.append(gears_internal)

  def GearsFactory(self, identifier, target='Release'):
    gclient_spec = self.BuildGClientSpec()
    factory = self.BaseFactory(gclient_spec)

    chromium_cmd_obj = gears_commands.GearsCommands(factory, identifier,
                                                    target, 'src/chrome',
                                                    self._target_platform)

    # Add the chrome compile step.
    chromium_cmd_obj.AddCompileStep(self._project)

    # Add the gears compile step.
    mode = None
    if target == 'Release':
      mode = 'opt'

    # Gears doesn't do incremental builds, so clean first then make.
    chromium_cmd_obj.AddGearsMake(mode, clean=True)

    # Add test step.
    chromium_cmd_obj.AddGearsTests(mode)
    return factory

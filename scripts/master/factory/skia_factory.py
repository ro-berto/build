#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the Skia master BuildFactory's.

Based on gclient_factory.py and adds Skia-specific steps."""

from master.factory import gclient_factory
from master.factory import skia_commands

import config

class SkiaFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the Skia master.cfg files."""

  def __init__(self, build_subdir, target_platform=None, default_timeout=600,
               environment_variables=None):
    """Instantiates a SkiaFactory as appropriate for this target_platform.

    build_subdir: string indicating path within slave directory
    target_platform: a string such as skia_commands.TARGET_PLATFORM_LINUX
    default_timeout: default timeout for each command, in seconds
    environment_variables: dictionary of environment variables that should
        be passed to all commands
    """
    # The only thing we use the BaseFactory for is to deal with gclient.
    gclient_solution = gclient_factory.GClientSolution(
        svn_url=config.Master.skia_url + 'trunk', name=build_subdir)
    gclient_factory.GClientFactory.__init__(
        self, build_dir='', solutions=[gclient_solution],
        target_platform=target_platform)
    self._factory = self.BaseFactory(factory_properties=None)

    # Get an implementation of SkiaCommands as appropriate for
    # this target_platform.
    self._skia_cmd_obj = skia_commands.CreateSkiaCommands(
        target_platform=target_platform, factory=self._factory,
        target='release', build_subdir=build_subdir, target_arch=None,
        default_timeout=default_timeout,
        environment_variables=environment_variables)

  def Build(self, clobber=True):
    """Build and return the complete BuildFactory.

    clobber: boolean indicating whether we should clean before building
        (Skia makefiles do not map dependencies quite right, so we always clean)
    """
    if clobber:
      self._skia_cmd_obj.AddClean()
    self._skia_cmd_obj.AddBuild(build_target='out/libskia.a',
                                description='BuildLibrary')
    self._skia_cmd_obj.AddBuild(build_target='tests',
                                description='BuildTests')
    self._skia_cmd_obj.AddRun(run_command='out/tests/tests',
                              description='RunTests')
    self._skia_cmd_obj.AddBuild(build_target='gm',
                                description='BuildGM')
    self._skia_cmd_obj.AddRun(run_command='out/gm/gm -r gm/base-linux',
                              description='RunGM')
    return self._factory

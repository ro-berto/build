#!/usr/bin/python
# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to add gears-specific commands to a BuildFactory.

Based on commands.py."""

from buildbot.steps import shell

import chromium_config as config
import chromium_step
import chromium_utils
import commands


class GearsCommands(commands.FactoryCommands):
  """Encapsulates data and methods to add commands to a BuildFactory."""

  def __init__(self, factory=None, identifier=None, target=None,
               build_dir=None, target_platform=None):
    commands.FactoryCommands.__init__(self, factory, identifier,
                                      target, build_dir, target_platform)

    # Gears test runner lives in the gears src tree.
    self._gears_test_runner = self.PathJoin('src', 'gears', 'gears',
                                            'test', 'runner', 'bootstrap.py')

    # Gears working dir.
    self._gears_root = self.PathJoin('build', 'src', 'gears', 'gears')

  def AddGearsMake(self, mode, clean=True):
    """Adds a step to the factory to build gears using make."""
    # Making gears from the open source repo requires a lot of setup,
    # so to simplify things this helper script is required to be
    # available on the builder.
    setup_env_and_make = r'c:\make_gears.bat'
    mode = mode or 'dbg'
    if clean:
      command_list = ['RD', '/S', '/Q', 'bin-%s' % mode]
      clean_timeout = 60
      self._factory.addStep(shell.ShellCommand,
                            description='make gears clean',
                            timeout=clean_timeout,
                            workdir=self._gears_root,
                            command=command_list)

    command_list = [setup_env_and_make, 'BROWSER=NPAPI',
                    'MODE=%s' % mode]
    gears_make_timeout = 300
    self._factory.addStep(shell.ShellCommand,
                          description='make gears %s' % mode,
                          timeout=gears_make_timeout,
                          workdir=self._gears_root,
                          command=command_list)

  def AddGearsTests(self, mode):
    """Adds a step to the factory to run the gears browser tests."""
    command_list = [self._python, self._gears_test_runner,
                    'chromium', mode or 'Debug']
    browser_test_timeout = 120
    self.AddTestStep(shell.ShellCommand, 'Gears browser tests',
                     browser_test_timeout, command_list)

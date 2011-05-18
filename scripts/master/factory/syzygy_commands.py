#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds chromium-specific commands."""

from buildbot.steps import shell


from master.factory import commands


class SyzygyCommands(commands.FactoryCommands):
  """Encapsulates methods to add Syzygy commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, target_arch=None):
    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    self._arch = target_arch
    self._factory = factory

  def AddClean(self):
    """Does a 'make clean'"""
    cmd = 'make -C Syzygy clean'
    self._factory.addStep(shell.ShellCommand,
                          description='Clean',
                          timeout=600,
                          command=cmd)

  def AddBuild(self):
    """Adds a compile step to the build."""
    cmd = 'make -C Syzygy'
    self._factory.addStep(shell.ShellCommand,
                          description='Build',
                          timeout=600,
                          command=cmd)

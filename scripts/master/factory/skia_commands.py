#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds chromium-specific commands."""

from buildbot.steps import shell


from master.factory import commands


class SkiaCommands(commands.FactoryCommands):
  """Encapsulates methods to add Skia commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, target_arch=None):
    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    self._arch = target_arch
    self._factory = factory

  def AddBuild(self):
    """Adds a compile step to the build."""
    cmd = 'make -C Skia'
    self._factory.addStep(shell.ShellCommand,
                          description='Build',
                          timeout=600,
                          command=cmd)

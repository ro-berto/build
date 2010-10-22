#!/usr/bin/python
# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds chromium-specific commands."""

from buildbot.steps import shell

from master.factory import commands
import config


class V8Commands(commands.FactoryCommands):
  """Encapsulates methods to add v8 commands to a buildbot factory."""

  def __init__(self, factory=None, identifier=None, target=None,
               build_dir=None, target_platform=None):

    commands.FactoryCommands.__init__(self, factory, identifier,
                                      target, build_dir, target_platform)

    # override _script_dir - one below because we run our build inside
    # the bleeding_edge directory
    self._script_dir = self.PathJoin('..', self._script_dir)

    # Where to point waterfall links for builds and test results.
    self._archive_url = config.Master.archive_url

    # Where the v8 slave scritps are.
    self._v8_script_dir = self.PathJoin(self._script_dir, 'v8')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')

    self._es5conform_dir = self.PathJoin('bleeding_edge/test/es5conform/data')
    self._es5conform_url = config.Master.es5conform_root_url
    self._es5conform_revision = config.Master.es5conform_revision

    if self._target_platform == 'win32':
      # Override to use the right python
      python_path = self.PathJoin('..', 'src', 'third_party', 'python_24')
      self._python = self.PathJoin(python_path, 'python_slave')

    # Create smaller name for the functions and vars to siplify the code below.
    J = self.PathJoin
    s_dir = self._v8_script_dir

    self._v8_test_tool = J(self._build_dir, 'tools')

    # Scripts in the v8 scripts dir.
    self._v8testing_tool = J(s_dir, 'v8testing.py')
    self._v8_es5conform_tool = J(s_dir, 'v8_es5conform.py')

  def AddV8Testing(self, properties=None):
    cmd = [self._python, self._v8testing_tool,
           '--target', self._target]
    if (self._target_platform == 'win32'):
      self.AddTaskkillStep()
    self.AddTestStep(shell.ShellCommand,
                     'Check', cmd,
                     workdir='build/bleeding_edge/')

  def AddV8ES5Conform(self, properties=None):
    cmd = [self._python, self._v8testing_tool,
           '--target', self._target,
           '--testname', 'es5conform']
    if (self._target_platform == 'win32'):
      self.AddTaskkillStep()
    self.AddTestStep(shell.ShellCommand,
                     'ES5-Conform',
                     cmd,
                     workdir='build/bleeding_edge/')

  def AddV8Mozilla(self, properties=None):
    cmd = [self._python, self._v8testing_tool,
           '--target', self._target,
           '--build-dir', self._build_dir,
           '--testname', 'mozilla']

    self.AddTestStep(shell.ShellCommand, 'Mozilla', cmd,
                     workdir='build/bleeding_edge/')

  def AddV8Sputnik(self, properties=None):
    cmd = [self._python, self._v8testing_tool,
           '--target', self._target,
           '--testname', 'sputnik']
    if (self._target_platform == 'win32'):
      self.AddTaskkillStep()
    self.AddTestStep(shell.ShellCommand, 'Sputnik', cmd,
                     workdir='build/bleeding_edge/')

  def AddArmSimTest(self, properties=None):
    cmd = [self._python, self._v8testing_tool,
           '--target', self._target,
           '--build-dir', self._build_dir,
           '--simulator', 'arm']
    self.AddTestStep(shell.ShellCommand, 'Arm test on simulator', cmd,
                     workdir='build/bleeding_edge/')

  def AddPresubmitTest(self, properties=None):
    cmd = [self._python, self._v8testing_tool,
           '--testname', 'presubmit']
    self.AddTestStep(shell.ShellCommand, 'Presubmit', cmd,
                     workdir='build/bleeding_edge/')

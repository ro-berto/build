#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds chromium-specific commands."""

from buildbot.steps import shell

from master.factory import commands
import config


class V8Commands(commands.FactoryCommands):
  """Encapsulates methods to add v8 commands to a buildbot factory."""

  # pylint: disable-msg=W0212
  # (accessing protected member V8)
  PERF_BASE_URL = config.Master.V8.perf_base_url

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, target_arch=None, crankshaft=False,
               shard_count=1, shard_run=1):

    commands.FactoryCommands.__init__(self, factory, target, build_dir, target_platform)

    # Override _script_dir - one below because we run our build inside
    # the bleeding_edge directory.
    self._script_dir = self.PathJoin('..', self._script_dir)

    # Where to point waterfall links for builds and test results.
    self._archive_url = config.Master.archive_url

    # Where the v8 slave scritps are.
    self._v8_script_dir = self.PathJoin(self._script_dir, 'v8')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')

    self._es5conform_dir = self.PathJoin('bleeding_edge/test/es5conform/data')
    self._es5conform_url = config.Master.es5conform_root_url
    self._es5conform_revision = config.Master.es5conform_revision

    self._arch = target_arch
    self._shard_count = shard_count
    self._shard_run = shard_run
    self._crankshaft = crankshaft

    if self._target_platform == 'win32':
      # Override to use the right python
      python_path = self.PathJoin('..', 'src', 'third_party', 'python_24')
      self._python = self.PathJoin(python_path, 'python_slave')

    # Create smaller name for the functions and vars to siplify the code below.
    J = self.PathJoin

    self._archive_tool = J(self._v8_script_dir, 'archive_v8.py')
    self._v8_test_tool = J(self._build_dir, 'tools')

    # Scripts in the v8 scripts dir.
    self._v8testing_tool = J(self._v8_script_dir, 'v8testing.py')

  def GetV8TestingCommand(self, simulator):
    cmd = [self._python, self._v8testing_tool,
           '--target', self._target]
    if simulator:
      cmd += ['--simulator', simulator]
    if self._arch:
      cmd += ['--arch', self._arch]
    if self._crankshaft:
      cmd += ['--crankshaft', 'on']
    if self._shard_count > 1:
      cmd += ['--shard_count', self._shard_count,
              '--shard_run', self._shard_run]
    return cmd

  def AddV8Testing(self, properties=None, simulator=None):
    if self._target_platform == 'win32':
      self.AddTaskkillStep()
    cmd = self.GetV8TestingCommand(simulator)
    self.AddTestStep(shell.ShellCommand,
                     'Check', cmd,
                     workdir='build/bleeding_edge/')

  def AddV8ES5Conform(self, properties=None, simulator=None):
    if self._target_platform == 'win32':
      self.AddTaskkillStep()
    cmd = self.GetV8TestingCommand(simulator)
    cmd += ['--testname', 'es5conform']
    self.AddTestStep(shell.ShellCommand,
                     'ES5-Conform',
                     cmd,
                     workdir='build/bleeding_edge/')

  def AddV8Mozilla(self, properties=None, simulator=None):
    if self._target_platform == 'win32':
      self.AddTaskkillStep()
    cmd = self.GetV8TestingCommand(simulator)
    cmd += ['--testname', 'mozilla']
    # Running tests in the arm simulator may take longer than 600 ms.
    mozilla_timeout = 600
    if simulator:
      mozilla_timeout = 1200
    self.AddTestStep(shell.ShellCommand, 'Mozilla', cmd,
                     timeout=mozilla_timeout, workdir='build/bleeding_edge/')

  def AddV8Sputnik(self, properties=None, simulator=None):
    if self._target_platform == 'win32':
      self.AddTaskkillStep()
    cmd = self.GetV8TestingCommand(simulator)
    cmd += ['--testname', 'sputnik']
    self.AddTestStep(shell.ShellCommand, 'Sputnik', cmd,
                     workdir='build/bleeding_edge/')

  def AddPresubmitTest(self, properties=None):
    cmd = [self._python, self._v8testing_tool,
           '--testname', 'presubmit']
    self.AddTestStep(shell.ShellCommand, 'Presubmit', cmd,
                     workdir='build/bleeding_edge/')

  def AddFuzzer(self, properties=None):
    cmd = ['./fuzz-v8.sh']
    self.AddTestStep(shell.ShellCommand, 'Fuzz', cmd,
                     workdir='build/bleeding_edge/')

  def AddLeakTests(self, properties=None):
    cmd = [self._python, self._v8testing_tool,
           '--testname', 'leak']
    env = {
      'PATH': (
        self._build_dir + '../src/third_party/valgrind/linux_x86/bin;'
      ),
      'VALGRIND_LIB': (
        self._build_dir + '../src/third_party/valgrind/linux_x86/lib/valgrind'
      ),
    }
    self.AddTestStep(shell.ShellCommand, 'leak', cmd,
                     env=env,
                     workdir='build/bleeding_edge/')

  def AddArchiveBuild(self, mode='dev', show_url=True,
      extra_archive_paths=None):
    """Adds a step to the factory to archive a build."""
    cmd = [self._python, self._archive_tool, '--target', self._target]
    self.AddTestStep(shell.ShellCommand, 'Archiving', cmd,
                 workdir='build/bleeding_edge')

  def AddMoveExtracted(self):
    """Adds a step to download and extract a previously archived build."""
    cmd = ('cp -R sconsbuild/release/* bleeding_edge/.')
    self._factory.addStep(shell.ShellCommand,
                          description='Move extracted to bleeding',
                          timeout=600,
                          workdir='build',
                          command=cmd)

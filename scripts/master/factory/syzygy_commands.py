# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds Syzygy-specific commands."""

from buildbot.process.properties import WithProperties
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
  
  def AddRandomizeChromeStep(self):
    # Randomization script path.
    script_path = self.PathJoin(self._build_dir, 'internal', 'build',
                                'randomize_chrome.py')
    command = [self._python, script_path,
               '--build-dir=%s' % self._build_dir,
               '--target=%s' % self._target,
               '--verbose']
    self.AddTestStep(shell.ShellCommand, 'Randomly Reorder Chrome', command)

  def AddBenchmarkChromeStep(self):
    # Benchmark script path.
    script_path = self.PathJoin(self._build_dir, 'internal', 'build',
                                'benchmark_chrome.py')
    command = [self._python, script_path,
               '--build-dir=%s' % self._build_dir,
               '--target=%s' % self._target,
               '--verbose']
    self.AddTestStep(shell.ShellCommand, 'Benchmark Chrome', command)

  def AddGenerateCoverage(self):
    # Coverage script path.
    script_path = self.PathJoin(self._build_dir, 'build',
                                'generate_coverage.py')
    command = [self._python,
               script_path,
               '--verbose',
               '--build-dir',
               self.PathJoin(self._build_dir, self._target)]
    self.AddTestStep(shell.ShellCommand, 'Capture Unittest Coverage', command)

    # Store the coverage results by the checkout revision.
    dst_path = 'gs://syzygy-archive/builds/coverage/%(got_revision)s'
    command = [self._python,
               self.PathJoin(self._script_dir, 'syzygy/gsutil_cp_dir.py'),
               self.PathJoin(self._build_dir, self._target, 'cov'),
               WithProperties(dst_path), ]
    self._factory.addStep(shell.ShellCommand, name='archive',
                          description='Archive Coverage Report',
                          command=command)

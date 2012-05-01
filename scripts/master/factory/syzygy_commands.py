# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds Syzygy-specific commands."""

from buildbot.process.properties import WithProperties
from buildbot.steps import shell

from master.factory import commands


class _UrlStatusCommand(shell.ShellCommand):
  """A ShellCommand subclass that adorns its build status with a URL on success.
  """
  def __init__(self, extra_text=None, **kw):
    """Initialize the buildstep.

    Args:
         extra_text: a tuple of (name, url) to pass to addUrl on successful
            completion.
    """
    self._extra_text = extra_text
    shell.ShellCommand.__init__(self, **kw)

    # Record our argument for the factory.
    self.addFactoryArguments(extra_text=extra_text)

  def commandComplete(self, cmd):
    """On success, add the URL provided to our status."""
    if cmd.rc == 0 and self._extra_text:
      (name, url) = self._extra_text
      self.addURL(self.build.render(name), self.build.render(url))


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
    script_path = self.PathJoin(self._build_dir, '..', 'syzygy',
                                'internal', 'build', 'randomize_chrome.py')
    command = [self._python, script_path,
               '--build-dir=%s' % self._build_dir,
               '--target=%s' % self._target,
               '--verbose']
    self.AddTestStep(shell.ShellCommand, 'Randomly Reorder Chrome', command)

  def AddBenchmarkChromeStep(self):
    # Benchmark script path.
    script_path = self.PathJoin(self._build_dir, '..', 'syzygy',
                                'internal', 'build', 'benchmark_chrome.py')
    command = [self._python, script_path,
               '--build-dir=%s' % self._build_dir,
               '--target=%s' % self._target,
               '--verbose']
    self.AddTestStep(shell.ShellCommand, 'Benchmark Chrome', command)

  def AddGenerateCoverage(self):
    # Coverage script path.
    script_path = self.PathJoin(self._build_dir, '..', 'syzygy', 'build',
                                'generate_coverage.py')
    command = [self._python,
               script_path,
               '--verbose',
               '--build-dir',
               self.PathJoin(self._build_dir, self._target)]
    self.AddTestStep(shell.ShellCommand, 'Capture Unittest Coverage', command)

    # Store the coverage results by the checkout revision.
    src_dir = self.PathJoin(self._build_dir, self._target, 'cov')
    dst_gs_url = WithProperties(
        'gs://syzygy-archive/builds/coverage/%(got_revision)s')
    url = WithProperties(
        'http://syzygy-archive.commondatastorage.googleapis.com/builds/'
           'coverage/%(got_revision)s/index.html')

    command = [self._python,
               self.PathJoin(self._script_dir, 'syzygy/gsutil_cp_dir.py'),
               src_dir,
               dst_gs_url,]

    self._factory.addStep(_UrlStatusCommand,
                          command=command,
                          extra_text=('Coverage Report', url),
                          name='archive',
                          description='Archive Coverage Report')

  def AddSmokeTest(self):
    # Smoke-test script path.
    script_path = self.PathJoin(self._build_dir, '..', 'syzygy', 'internal',
                                'build', 'smoke_test.py')

    # We pass in the root build directory to the smoke-test script. It will
    # place its output in <build_dir>/smoke_test, alongside the various
    # configuration sub-directories.
    command = [self._python,
               script_path,
               '--verbose',
               '--build-dir',
               self._build_dir]

    self._factory.addStep(shell.ShellCommand, 'Smoke Test', command)

  def AddArchival(self):
    '''Adds steps to archive the build output for official builds.'''
    # Store the coverage results by the checkout revision.
    src_archive = self.PathJoin(self._build_dir, self._target, 'benchmark.zip')
    dst_gs_url = WithProperties(
        'gs://syzygy-archive/builds/official/%(got_revision)s/benchmark.zip')
    url = WithProperties(
        'http://syzygy-archive.commondatastorage.googleapis.com/builds/'
           'official/%(got_revision)s/benchmark.zip')

    command = [self._python,
               self.PathJoin(self._script_dir, 'syzygy/gsutil_cp_dir.py'),
               src_archive,
               dst_gs_url,]

    self._factory.addStep(_UrlStatusCommand,
                          command=command,
                          extra_text=('Build archive', url),
                          name='archive',
                          description='Build archive')

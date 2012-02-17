#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

Contains the Dart specific commands. Based on commands.py
"""

from buildbot.steps import shell
from buildbot.process.properties import WithProperties

from master import chromium_step
from master.factory import commands


class DartCommands(commands.FactoryCommands):
  """Encapsulates methods to add dart commands to a buildbot factory."""

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    # One additional directory up compared to normal chromium scripts due
    # to using runtime or dartc as runtime dir inside build.
    self._script_dir = self.PathJoin('..', self._script_dir)

    # Where the chromium slave scripts are.
    self._chromium_script_dir = self.PathJoin(self._script_dir, 'chromium')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')

    self._slave_dir = self.PathJoin(self._script_dir,
                                            '..', '..', '..',
                                            'build', 'scripts',
                                            'slave', 'dart')

    self._dart_util = self.PathJoin(self._slave_dir, 'dart_util.py')
    self._vm_build_dir = self.PathJoin('build', 'runtime')
    self._dartc_build_dir = self.PathJoin('build', 'compiler')
    self._repository_root = ''
    self._target_platform = target_platform


  def AddMaybeClobberStep(self, clobber, options=None, timeout=1200):
    """Possibly clobber.

    Either clobber unconditionally (e.g. nuke-and-pave builder, set at
    factory build time), or at runtime (clobber checkbox).  If the
    former, the clobber arg is set.  If the latter, we use a buildbot
    Properties object.

    TODO(jrg); convert into a doStepIf with a closure referencing
    step.build.getProperties().  E.g.
    http://permalink.gmane.org/gmane.comp.python.buildbot.devel/6039
    """
    options = options or {}
    clobber_cmd = [self._python, self._dart_util]
    clobber_cmd.append(WithProperties('%(clobber:+--clobber)s'))
    if options.get('arch') == 'dartc':
      workdir = self._dartc_build_dir
    else:
      workdir = self._vm_build_dir
    self._factory.addStep(shell.ShellCommand,
                          name='maybe clobber',
                          description='maybe clobber',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=workdir,
                          command=clobber_cmd)

  # pylint: disable=W0221
  def AddCompileStep(self, options=None, timeout=1200):
    options = options or {}
    cmd = 'python ../tools/build.py --mode=%s' % (options['mode'])
    if options.get('arch') == 'dartc':
      workdir = self._dartc_build_dir
    else:
      cmd += ' --arch=%s' % (options['arch'])
      workdir = self._vm_build_dir
    self._factory.addStep(shell.ShellCommand,
                          name='build',
                          description='build',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=workdir,
                          command=cmd)

  def AddTests(self, options=None, timeout=1200):
    options = options or {}
    if options.get('arch') == 'dartc':
      component = 'dartc'
      arch = 'ia32'
    else:
      component = 'vm'
      arch = options.get('arch')

    configuration = (options['mode'], arch, component)
    base_cmd = ('python ../tools/test.py --progress=line --report'
        ' --time --mode=%s --arch=%s --component=%s') % configuration
    if options.get('arch') == 'dartc':
      cmd = base_cmd
      self._factory.addStep(shell.ShellCommand,
                            name='tests',
                            description='tests',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._dartc_build_dir,
                            command=cmd)
    else:
      cmd = base_cmd
      self._factory.addStep(shell.ShellCommand,
                            name='tests',
                            description='tests',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._vm_build_dir,
                            command=cmd)
      # Rerun all tests in checked mode (assertions and type tests).
      cmd = base_cmd + ' --checked'
      self._factory.addStep(shell.ShellCommand,
                            name='checked_tests',
                            description='checked_tests',
                            timeout=timeout,
                            haltOnFailure=True,
                            workdir=self._vm_build_dir,
                            command=cmd)

  def AddAnnotatedSteps(self, python_script, timeout=1200):
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name='annotated_steps',
                          description='annotated_steps',
                          timeout=timeout,
                          haltOnFailure=True,
                          command=[self._python, python_script])

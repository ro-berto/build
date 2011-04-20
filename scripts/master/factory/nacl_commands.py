#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

Contains the Native Client specific commands. Based on commands.py"""

from buildbot.steps import trigger

from master import chromium_step
from master.factory import commands
from master.log_parser import process_log

import config


class NativeClientCommands(commands.FactoryCommands):
  """Encapsulates methods to add nacl commands to a buildbot factory."""

  # pylint: disable-msg=W0212
  # (accessing protected member _NaClBase)
  PERF_BASE_URL = config.Master._NaClBase.perf_base_url

  def __init__(self, factory=None, build_dir=None, target_platform=None):
    commands.FactoryCommands.__init__(self, factory, 'Release', build_dir,
                                      target_platform)

  def AddTrigger(self, trigger_who):
    self._factory.addStep(trigger.Trigger(schedulerNames=[trigger_who],
                                          waitForFinish=True))

  def AddModularBuildStep(self, modular_build_type, timeout=1200):
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name='modular_build',
                          description='modular_build',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir='build/native_client/tools/modular-build',
                          command='python build_for_buildbot.py %s' %
                            modular_build_type)

  def AddAnnotatedStep(self, command, timeout=1200,
                       workdir='build/native_client', haltOnFailure=True,
                       factory_properties=None, usePython=False, env=None):
    factory_properties = factory_properties or {}
    env = env or {}
    if 'test_name' not in factory_properties:
      test_class = chromium_step.AnnotatedCommand
    else:
      test_name = factory_properties.get('test_name')
      test_class = self.GetPerfStepClass(
          factory_properties, test_name, process_log.GraphingLogProcessor,
          command_class=chromium_step.AnnotatedCommand)
    if usePython:
      command = [self._python] + command
    self._factory.addStep(test_class,
                          name='annotate',
                          description='annotate',
                          timeout=timeout,
                          haltOnFailure=haltOnFailure,
                          env=env,
                          workdir=workdir,
                          command=command)

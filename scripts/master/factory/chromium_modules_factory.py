# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

#
# TODO(nsylvain): Kill this file. The functionalities here can be replaced
# by using a new target in all.gyp.
#
"""Utility class to build the chromium submodule builders.

Based on chromium_factory.py."""

from master.factory import chromium_commands
from master.factory import chromium_factory


class ChromiumSubmodulesFactory(chromium_factory.ChromiumFactory):
  def __init__(self, target_platform=None):
    chromium_factory.ChromiumFactory.__init__(self, 'src/base',
                                              target_platform=target_platform)

  def SubmoduleFactory(self, identifier, target='Release', options=None,
                       mode=None, factory_properties=None,
                       slavelastic=False):
    # Create the spec for the solutions.
    tests = ['unit']
    gclient_spec = self.BuildGClientSpec(tests)

    # Create the factory.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties)

    # Create the factory commands object.
    base_cmd_obj = chromium_commands.ChromiumCommands(factory, identifier,
                                                      target, 'src/base',
                                                      self._target_platform)

    net_cmd_obj = chromium_commands.ChromiumCommands(factory, identifier,
                                                     target, 'src/net',
                                                     self._target_platform)

    if self._target_platform == 'win32':
      sandbox_cmd_obj = chromium_commands.ChromiumCommands(factory, identifier,
                                                        target, 'src/sandbox',
                                                        self._target_platform)

    if self._target_platform == 'linux2':
      base_solution = 'base.Makefile'
      net_solution = 'net.Makefile'
    elif self._target_platform == 'darwin':
      base_solution = 'base.xcodeproj'
      net_solution = 'net.xcodeproj'
    else:
      base_solution = 'base.sln'
      net_solution = 'net.sln'

    # Add the compile steps.
    base_cmd_obj.AddCompileStep(solution=base_solution,
                                description='compiling base',
                                descriptionDone='compile base',
                                options=options, mode=mode)

    net_cmd_obj.AddCompileStep(solution=net_solution,
                               description='compiling net',
                               descriptionDone='compile net',
                               options=options, mode=mode)

    if self._target_platform == 'win32':
      sandbox_cmd_obj.AddCompileStep(solution='sandbox.sln',
                                     description='compiling sandbox',
                                     descriptionDone='compile sandbox',
                                     options=options, mode=mode)

    factory_properties = factory_properties or {}

    if slavelastic:
      base_cmd_obj.AddSlavelasticTestStep('base_unittests', factory_properties)
      net_cmd_obj.AddSlavelasticTestStep('net_unittests', factory_properties)
    else:
      base_cmd_obj.AddBasicGTestTestStep('base_unittests', factory_properties)
      net_cmd_obj.AddBasicGTestTestStep('net_unittests', factory_properties)
      if self._target_platform == 'win32':
        sandbox_cmd_obj.AddBasicGTestTestStep('sbox_unittests')
        sandbox_cmd_obj.AddBasicGTestTestStep('sbox_integration_tests')
        sandbox_cmd_obj.AddBasicGTestTestStep('sbox_validation_tests')

    return factory

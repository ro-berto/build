#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a Dart-specific BuildFactory.

Based on gclient_factory.py.
"""

from master.factory import dart_commands
from master.factory import gclient_factory

import config


class DartFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the dart master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
  }

  NEEDED_COMPONENTS_INTERNAL = {
  }

  if config.Master.trunk_internal_url:
    CUSTOM_DEPS_JAVA = ('dart/third_party/java',
                        config.Master.trunk_internal_url +
                        '/third_party/openjdk')

  def __init__(self, build_dir, target_platform=None, trunk=False):
    solutions = []
    self.target_platform = target_platform
    deps_file = '/deps/all.deps'
    dart_url = config.Master.dart_bleeding + deps_file
    # If this is trunk use the deps file from there instead.
    if trunk:
      dart_url = config.Master.dart_trunk + deps_file
    custom_deps_list = []

    if config.Master.trunk_internal_url:
      custom_deps_list.append(self.CUSTOM_DEPS_JAVA)

    main = gclient_factory.GClientSolution(
        dart_url,
        needed_components=self.NEEDED_COMPONENTS,
        custom_deps_list = custom_deps_list)
    solutions.append(main)

    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform)

  def DartFactory(self, target='Release', clobber=False, tests=None,
                  slave_type='BuilderTester', options=None,
                  compile_timeout=1200, build_url=None,
                  factory_properties=None, env=None):
    factory_properties = factory_properties or {}
    tests = tests or []
    # Create the spec for the solutions
    factory_properties['gclient_transitive'] = True
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    dart_cmd_obj = dart_commands.DartCommands(factory,
                                              target,
                                              self._build_dir,
                                              self._target_platform,
                                              env=env)

    # We must always add the MaybeClobberStep, since this factory is
    # created at master start, but the choice of clobber or not may be
    # chosen at runtime (e.g. check the 'clobber' box).
    dart_cmd_obj.AddMaybeClobberStep(clobber, options=options)

    # Add the compile step if needed.
    if slave_type in ['BuilderTester', 'Builder', 'Trybot']:
      dart_cmd_obj.AddCompileStep(options=options,
                                  timeout=compile_timeout)

    # Add all the tests.
    if slave_type in ['BuilderTester', 'Trybot', 'Tester']:
      dart_cmd_obj.AddTests(options=options)

    return factory

  def DartAnnotatedFactory(self, python_script,
                           target='Release', tests=None,
                           timeout=1200, factory_properties=None,
                           env=None):
    factory_properties = factory_properties or {}
    tests = tests or []
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    dart_cmd_obj = dart_commands.DartCommands(factory,
                                              target,
                                              self._build_dir,
                                              self._target_platform,
                                              env=env)
    dart_cmd_obj.AddAnnotatedSteps(python_script, timeout=timeout)
    return factory

#!/usr/bin/python
# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a Native-Client-SDK-specific BuildFactory.

Based on gclient_factory.py."""

import os
import re

import chromium_config as config
import nacl_sdk_commands
import gclient_factory


class NativeClientSDKFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the nacl.sdk master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
  }

  NEEDED_COMPONENTS_INTERNAL = {
  }

  def __init__(self, build_dir, target_platform=None, use_supplement=False,
               alternate_url=None):
    solutions = []
    self.target_platform = target_platform
    nacl_sdk_url = config.Master.nacl_sdk_url
    if alternate_url:
      nacl_sdk_url = alternate_url
    main = gclient_factory.GClientSolution(
        nacl_sdk_url,
        needed_components=self.NEEDED_COMPONENTS)
    solutions.append(main)

    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform)


  def _AddTests(self, factory_cmd_obj, tests, target,
                mode=None, factory_properties=None, options=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    factory_properties = factory_properties or {}
    # This function is too crowded, try to simplify it a little.
    def R(test):
      return gclient_factory.ShouldRunTest(tests, test)
    f = factory_cmd_obj

    # no tests yet

  def NativeClientSDKFactory(self, identifier, target='Release', clobber=False,
                             tests=None, mode=None, slave_type='BuilderTester',
                             options=None, compile_timeout=1200, build_url=None,
                             factory_properties=None, official_release=True):
    factory_properties = factory_properties or {}
    tests = tests or []
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               official_release=official_release,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    nacl_sdk_cmd_obj = nacl_sdk_commands.NativeClientSDKCommands(
        factory, identifier,
        target,
        self._build_dir,
        self._target_platform)

    # Add the compile step if needed.
    if (slave_type == 'BuilderTester' or slave_type == 'Builder' or
        slave_type == 'Trybot'):
      nacl_sdk_cmd_obj.AddCompileStep(mode=mode, clobber=clobber,
                                      options=options, timeout=compile_timeout)
      nacl_sdk_cmd_obj.AddTarballStep()
      
    # Add this archive build step.
    if factory_properties.get('archive_build'):
      nacl_sdk_cmd_obj.AddArchiveBuild(
          factory_properties['archive_src'],
          factory_properties['archive_dst_base'],
          factory_properties['archive_dst'],
          data_description='to revision')
      if factory_properties.get('archive_dst_latest'):
        nacl_sdk_cmd_obj.AddArchiveBuild(
            factory_properties['archive_src'],
            factory_properties['archive_dst_base'],
            factory_properties['archive_dst_latest'],
            data_description='to latest')

    # Download the full output directory if the machine is a tester.
    if slave_type == 'Tester':
      nacl_sdk_cmd_obj.AddExtractBuild(factory_properties.get('archive_url'))

    # Add all the tests.
    self._AddTests(nacl_sdk_cmd_obj, tests, target, mode, factory_properties,
                   options)
    return factory

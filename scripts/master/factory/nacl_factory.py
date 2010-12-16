#!/usr/bin/python
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a Native-Client-specific BuildFactory.

Based on gclient_factory.py."""

from master.factory import gclient_factory
from master.factory import nacl_commands

import config


generic_partial_sdk = (
     '%s --verbose --mode=nacl_extra_sdk %s '
     '--download extra_sdk_update_header '
     'install_libpthread extra_sdk_update '
)

win_m32_n32_options = {
    'partial_sdk': generic_partial_sdk % ('scons.bat', 'platform=x86-32'),
    'scons_opts': 'platform=x86-32',
}

win_m64_n64_options = {
    'partial_sdk': generic_partial_sdk % ('scons.bat',
                                          'platform=x86-64 sdl=none'),
    'scons_opts': 'platform=x86-64 sdl=none',
}

win_m64_n64_tester_options = {
    'partial_sdk': generic_partial_sdk % ('scons.bat',
                                          'platform=x86-64 sdl=none'),
    'scons_opts': (
        'platform=x86-64 sdl=none built_elsewhere=1 '
        'naclsdk_mode=manual naclsdk_validate=0 '),
}

generic_m32_n32_options = {
    'partial_sdk': generic_partial_sdk % ('./scons', 'platform=x86-32'),
    'scons_opts': 'platform=x86-32',
}

generic_m64_n32_options = {
    'partial_sdk': generic_partial_sdk % ('./scons', 'buildplatform=x86-64'),
    'scons_opts': 'buildplatform=x86-64',
}

generic_m64_n64_options = {
    'partial_sdk': generic_partial_sdk % ('./scons', 'platform=x86-64'),
    'scons_opts': 'platform=x86-64',
}

hardy64_m64_n64_options = {
    'partial_sdk': generic_partial_sdk % ('./scons', 'platform=x86-64'),
    'scons_opts': 'platform=x86-64 --disable_hardy64_vmware_failures',
}

arm_emu_partial_sdk = (
     'bash -c " '
     './scons --verbose --download --mode=nacl_extra_sdk '
     'platform=arm bitcode=1 sdl=none '
     'extra_sdk_clean extra_sdk_update_header '
     'install_libpthread extra_sdk_update '
     ' "'
)

arm_emu_options = {
    'scons_opts':
        ('platform=arm bitcode=1 sdl=none '),
}
arm_tester_options = {
    'scons_prefix': 'ARM_CC=gcc ARM_CXX=g++ ARM_LIB_DIR=/usr/lib ',
    'scons_opts':
        ('platform=arm bitcode=1 '
         'sdl=none '
         'built_elsewhere=1 '
         'naclsdk_mode=manual naclsdk_validate=0'),
}
linux_marm_narm_options = {}
for build_mode in ('dbg', 'opt'):
  # For emulated ARM.
  linux_marm_narm_options[build_mode] = arm_emu_options.copy()
  linux_marm_narm_options[build_mode]['partial_sdk'] = (
    arm_emu_partial_sdk % {'mode': '%s-linux' % build_mode})

  # For ARM tests.
  linux_marm_narm_options[build_mode + '-arm'] = arm_tester_options.copy()

  # For ARM trybot.
  linux_marm_narm_options[build_mode + '-arm-try'] = arm_emu_options.copy()
  linux_marm_narm_options[build_mode + '-arm-try']['partial_sdk'] = (
    arm_emu_partial_sdk % {'mode': '%s-linux' % build_mode})


class NativeClientFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the nacl master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
  }

  NEEDED_COMPONENTS_INTERNAL = {
  }

  def __init__(self, build_dir, target_platform=None, use_supplement=False,
               alternate_url=None, custom_deps_list=None):
    solutions = []
    self.target_platform = target_platform
    nacl_url = config.Master.nacl_url
    if alternate_url:
      nacl_url = alternate_url
    main = gclient_factory.GClientSolution(
        nacl_url,
        needed_components=self.NEEDED_COMPONENTS,
        custom_deps_list=custom_deps_list)
    solutions.append(main)

    if use_supplement:
      supplement = gclient_factory.GClientSolution(
          config.Master.nacl_trunk_url + '/deps/supplement.DEPS',
          needed_components=self.NEEDED_COMPONENTS_INTERNAL)
      solutions.append(supplement)
    else:
      doxygen = gclient_factory.GClientSolution(
          config.Master.nacl_trunk_url + '/deps/doxygen.DEPS',
          needed_components=self.NEEDED_COMPONENTS_INTERNAL)
      solutions.append(doxygen)

    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform)

  @staticmethod
  def _AddTests(factory_cmd_obj, tests, target,
                mode=None, factory_properties=None, options=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    factory_properties = factory_properties or {}
    # This function is too crowded, try to simplify it a little.
    def R(test):
      return gclient_factory.ShouldRunTest(tests, test)
    f = factory_cmd_obj

    for test_size in ['small', 'medium', 'large', 'smoke']:
      if R('nacl_%s_tests' % test_size):
        if test_size == 'large':
          timeout = 600
        else:
          timeout = 300
        f.AddSizedTests(test_size, options=options, timeout=timeout)

    if R('nacl_valgrind'):
      f.AddMemcheck(options=options)
      f.AddThreadSanitizer(options=options)
      f.AddThreadSanitizer(trusted=True, options=options)
      f.AddThreadSanitizer(trusted=True, hybrid=True, race_verifier=True,
                           options=options)

    if R('nacl_utman_arm_tests'):
      f.AddUtmanTests('arm', options=options)
    if R('nacl_utman_x86_32_tests'):
      f.AddUtmanTests('x86-32', options=options)
    if R('nacl_utman_x86_64_tests'):
      f.AddUtmanTests('x86-64', options=options)

    if R('nacl_coverage'):
      f.AddCoverageTests(options=options)

    if R('nacl_selenium'):
      f.AddSeleniumTests(options=options)

  @staticmethod
  def _AddTriggerTests(factory_cmd_obj, tests, target,
                       mode=None, factory_properties=None, options=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    # This function is too crowded, try to simplify it a little.
    def R(test):
      return gclient_factory.ShouldRunTest(tests, test)
    f = factory_cmd_obj

    for mode in ['dbg', 'opt']:
      if R('nacl_trigger_arm_hw_%s' % mode):
        f.AddTrigger('arm_%s_hw_tests' % mode)
      if R('nacl_trigger_win7atom64_hw_%s' % mode):
        f.AddTrigger('win7atom64_%s_hw_tests' % mode)

  def NativeClientFactory(self, target='Release', clobber=False, tests=None,
                          mode=None, slave_type='BuilderTester',
                          options=None, compile_timeout=1200, build_url=None,
                          official_release=False, factory_properties=None,
                          build_toolchain=False, just_trusted=False,
                          toolchain_bits='multilib', test_target=None,
                          git_toolchain=False):
    factory_properties = factory_properties or {}
    options = options or {}
    tests = tests or []
    # Add build_toolchain into options.
    options = options.copy()
    options['build_toolchain'] = build_toolchain
    options['just_trusted'] = just_trusted
    options['toolchain_bits'] = toolchain_bits
    options['git_toolchain'] = git_toolchain
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               official_release=official_release,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    nacl_cmd_obj = nacl_commands.NativeClientCommands(factory,
                                                      target,
                                                      self._build_dir,
                                                      self._target_platform,
                                                      test_target=test_target)

    # Add the compile step if needed.
    if (slave_type == 'BuilderTester' or slave_type == 'Builder' or
        slave_type == 'Trybot'):
      nacl_cmd_obj.GClientRunHooks(mode=mode, options=options,
                                   timeout=compile_timeout)
      if factory_properties.get('nacl_tarball'):
        nacl_cmd_obj.AddTarballStep(factory_properties['nacl_tarball_name'])
      nacl_cmd_obj.AddCompileStep(solution=None, mode=mode, clobber=clobber,
                                  options=options, timeout=compile_timeout)

    # Download the full output directory if the machine is a tester.
    if slave_type == 'Tester':
      nacl_cmd_obj.AddExtractBuild(factory_properties.get('archive_url'))

    # Add all the tests.
    self._AddTests(nacl_cmd_obj, tests, target, mode, factory_properties,
                   options)

    # Optionally run coverage.
    coverage_dir = factory_properties.get('archive_coverage')
    if coverage_dir:
      nacl_cmd_obj.AddArchiveCoverage(coverage_dir)

    # Add this archive build step.
    if factory_properties.get('archive_build'):
      nacl_cmd_obj.DropDoxygen()
      nacl_cmd_obj.AddArchiveBuild(factory_properties['archive_src'],
                                   factory_properties['archive_dst_base'],
                                   factory_properties['archive_dst'])
      if factory_properties.get('archive_dst_latest'):
        nacl_cmd_obj.AddArchiveBuild(factory_properties['archive_src'],
                                     factory_properties['archive_dst_base'],
                                     factory_properties['archive_dst_latest'])
    # Trigger tests on other builders.
    self._AddTriggerTests(nacl_cmd_obj, tests, target, mode, factory_properties,
                          options)

    return factory

  def ModularBuildFactory(self, modular_build_type,
                          target='Release',
                          tests=None, slave_type='BuilderTester',
                          compile_timeout=1200,
                          official_release=False, factory_properties=None):
    factory_properties = factory_properties or {}
    tests = tests or []
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               official_release=official_release,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    nacl_cmd_obj = nacl_commands.NativeClientCommands(factory,
                                                      target,
                                                      self._build_dir,
                                                      self._target_platform)

    nacl_cmd_obj.AddModularBuildStep(modular_build_type,
                                     timeout=compile_timeout)

    return factory

  def AnnotatedFactory(self, command, target='Release',
                       workdir='build/native_client', official_release=False,
                       factory_properties=None, test_target=None):
    factory_properties = factory_properties or {}
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec([])
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               official_release=official_release,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    nacl_cmd_obj = nacl_commands.NativeClientCommands(factory,
                                                      target,
                                                      self._build_dir,
                                                      self._target_platform)

    # Single build action.
    nacl_cmd_obj.AddAnnotatedStep(command, timeout=9000,
                                  factory_properties=factory_properties)

    return factory

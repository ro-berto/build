# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a O3D-specific BuildFactory.

Based on gclient_factory.py"""

from master.factory import gclient_factory
from master.factory import o3d_commands

import config

class O3DFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the chromium master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  def __init__(self, build_dir, target_platform=None):
    main = gclient_factory.GClientSolution(config.Master.o3d_url)
    custom_deps_list = [main]
    if config.Master.o3d_url_internal:
      internal = gclient_factory.GClientSolution(config.Master.o3d_url_internal,
                                                 name='o3d-internal')
      custom_deps_list.append(internal)

    gclient_factory.GClientFactory.__init__(self, build_dir, custom_deps_list,
                                            target_platform=target_platform)

  def O3DFactory(self, identifier, clobber=False,
                 tests=None, mode=None, slave_type='BuilderTester',
                 options=None, compile_timeout=1200, build_url=None,
                 factory_properties=None):
    tests = tests or []
    if self._target_platform == 'darwin':
      if not mode:
        mode = 'test-opt-mac'
    else:
      if not mode:
        mode = 'test-opt-d3d'

    if self._target_platform == 'darwin':
      build_dir_extra = 'xcodebuild'
    elif self._target_platform == 'win32':
      build_dir_extra = 'o3d\\build'
    else:
      build_dir_extra = 'out'

    if 'opt' in mode:
      configuration = 'Release'
    else:
      configuration = 'Debug'

    if 'cb-gl' in mode:
      renderer = 'renderer=cb cb_service=gl'
    elif 'cb-d3d' in mode:
      renderer = 'renderer=cb cb_service=d3d9'
    elif self._target_platform == 'win32':
      renderer = 'renderer=d3d9'
    else:
      renderer = 'renderer=gl'

    factory_properties = factory_properties or {}

    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)

    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties)

    # Get the factory command object to create new steps to the factory.
    o3d_cmd_obj = o3d_commands.O3DCommands(
        factory, identifier,
        target=configuration,
        build_dir=build_dir_extra,
        target_platform=self._target_platform)

    # Add the compile step if needed.
    if (slave_type == 'BuilderTester' or slave_type == 'Builder' or
        slave_type == 'Trybot'):
      o3d_cmd_obj.GClientRunHooks(mode=mode, options=options,
                                  timeout=compile_timeout,
                                  env={'GYP_DEFINES': renderer})
      o3d_cmd_obj.AddCompileStep(solution=None, mode=mode, clobber=clobber,
                                 options=options, timeout=compile_timeout)
      if slave_type != 'Trybot':
        o3d_cmd_obj.AddArchiveTestPackageStep(
          factory_properties.get('archive_dir'))

    # Archive the full output directory if the machine is a builder.
    if slave_type == 'Builder':
      o3d_cmd_obj.AddZipBuild('o3d',
                              factory_properties.get('archive_include_files'))

    # Download the full output directory if the machine is a tester.
    if slave_type == 'Tester' and mode != 'Chromium':
      o3d_cmd_obj.AddUnpackTestArchiveStep(factory_properties.get('depend'))
      o3d_cmd_obj.AddUnitTestsStep(slave_type)
      o3d_cmd_obj.AddQATestStep()
    elif slave_type == 'Tester':
      o3d_cmd_obj.AddExtractBuild(build_url)
      o3d_cmd_obj.AddQATestStep()
    elif slave_type == 'Trybot' and (self._target_platform != 'win32' or
                                     '-cb' not in mode):
      o3d_cmd_obj.AddUnitTestsStep(slave_type)

    # Upload archived build.
    if factory_properties.get('upload_archived_build'):
      o3d_cmd_obj.AddUploadZipBuild()

    # Add all the tests.
    self._AddTests(o3d_cmd_obj, tests, mode, factory_properties)

    return factory

  @staticmethod
  def _AddTests(factory_cmd_obj, tests, mode, factory_properties=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""

    browsers = ['firefox', 'googlechrome', 'iexplore', 'safari']
    performance_test_per_browser = {}
    factory_properties = factory_properties or {}
    f = factory_cmd_obj

    # The tests are run in the order specified because some will install plugin
    # and must be run before tests which require it to be installed.
    for test in tests:
      if test == 'pulse_tests':
        f.AddPulseTests(mode=mode,
                        factory_properties=factory_properties)

      for browser in browsers:
        if test == ('selenium-qa-' + browser):
          f.AddSeleniumQaTestStep(mode=mode,
                                  factory_properties=factory_properties,
                                  browser='*' + browser)
        if test == ('selenium-qa-' + browser + '-noinstall'):
          f.AddSeleniumQaTestStep(mode=mode,
                                  factory_properties=factory_properties,
                                  browser='*' + browser,
                                  install_o3d=False)

        if test == ('fps_' + browser):
          try:
            performance_test_per_browser[browser].append('TestSampleDisplayFps')
          except KeyError:
            performance_test_per_browser[browser] = ['TestSampleDisplayFps']

        if test == ('pagecycler_' + browser):
          try:
            performance_test_per_browser[browser].append('TestPageCycler')
          except KeyError:
            performance_test_per_browser[browser] = ['TestPageCycler']

    for browser in performance_test_per_browser:
      performance_test_names = performance_test_per_browser[browser]
      if performance_test_names:
        print 'adding:' + str(performance_test_names)
        f.AddPerformanceTestStep(tests=performance_test_names,
                                 factory_properties=factory_properties,
                                 browser='*' + browser)

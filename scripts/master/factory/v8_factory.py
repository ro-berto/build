#!/usr/bin/python
# Copyright (c) 2006-2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the v8 master BuildFactory's.

Based on gclient_factory.py and adds v8-specific steps."""

from buildbot.steps import trigger

from build_factory import BuildFactory
import v8_commands
import chromium_config as config
import gclient_factory


class V8Factory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the v8 master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform


  CUSTOM_DEPS_PYTHON = ('src/third_party/python_24',
                        config.Master.trunk_url +
                        '/deps/third_party/python_24')

  CUSTOM_DEPS_ES5CONFORM = ('bleeding_edge/test/es5conform/data',
                            'https://es5conform.svn.codeplex.com/svn@62998')

  CUSTOM_DEPS_SPUTNIK = ('bleeding_edge/test/sputnik/sputniktests',
                         'http://sputniktests.googlecode.com/svn/trunk@28')

  CUSTOM_DEPS_SCONS = ('third_party/scons',
                       'svn://chrome-svn.corp.google.com/chrome/trunk/src/third_party/scons')

  CUSTOM_DEPS_VALGRIND = ('src/third_party/valgrind',
     config.Master.trunk_url + '/deps/third_party/valgrind/binaries')

  CUSTOM_DEPS_MOZILLA = ('bleeding_edge/test/mozilla/data',
                          config.Master.trunk_url +
                          '/deps/third_party/mozilla-tests')




  def __init__(self, build_dir, target_platform=None):
    main = gclient_factory.GClientSolution(config.Master.v8_bleeding_edge)

    custom_deps_list = [main]

    gclient_factory.GClientFactory.__init__(self, build_dir, custom_deps_list,
                                            target_platform=target_platform)


  def _AddTests(self, factory_cmd_obj, tests, mode=None,
                factory_properties=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    factory_properties = factory_properties or {}

    # Small helper function to check if we should run a test
    def R(test):
      return gclient_factory.ShouldRunTest(tests, test)

    f = factory_cmd_obj

    if R('presubmit'): f.AddPresubmitTest()
    if R('v8testing'): f.AddV8Testing()
    if R('v8_es5conform'): f.AddV8ES5Conform()

    # Mozilla tests should be moved to v8 repo
    if R('mozilla'): 
      f.AddV8Mozilla()

    if R('sputnik'): f.AddV8Sputnik()
    if R('arm'): f.AddArmSimTest()


  def V8Factory(self, identifier, target='release', clobber=False,
                      tests=None, mode=None, slave_type='BuilderTester',
                      options=None, compile_timeout=1200, build_url=None,
                      project=None, factory_properties=None):
    tests = tests or []
    factory_properties = factory_properties or {}

    # Add scons which is not on a build slave by default
    self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_SCONS)

    # If we are on win32 add extra python executable
    if (self._target_platform == 'win32'):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_PYTHON)

    if (gclient_factory.ShouldRunTest(tests, 'v8_es5conform')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_ES5CONFORM)

    if (gclient_factory.ShouldRunTest(tests, 'sputnik')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_SPUTNIK)

    if (gclient_factory.ShouldRunTest(tests, 'leak')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_VALGRIND)
    
    if (gclient_factory.ShouldRunTest(tests, 'mozilla')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_MOZILLA)
    
    factory = self.BuildFactory(identifier, target, clobber, tests, mode,
                                slave_type, options, compile_timeout, build_url,
                                project, factory_properties)

    # Get the factory command object to create new steps to the factory.
    # Note - we give '' as build_dir as we use our own build in test tools
    v8_cmd_obj = v8_commands.V8Commands(factory, identifier,
                                        target,
                                        '',
                                        self._target_platform)
    # Add all the tests.
    self._AddTests(v8_cmd_obj, tests, mode, factory_properties)
    
    return factory

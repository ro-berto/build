#!/usr/bin/python
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the v8 master BuildFactory's.

Based on gclient_factory.py and adds v8-specific steps."""

from master.factory import v8_commands
from master.factory import gclient_factory
import config


class V8Factory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the v8 master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform


  CUSTOM_DEPS_PYTHON = ('src/third_party/python_24',
                        config.Master.trunk_url +
                        '/deps/third_party/python_24')

  CUSTOM_DEPS_ES5CONFORM = ('bleeding_edge/test/es5conform/data',
                            'https://es5conform.svn.codeplex.com/svn@71525')

  CUSTOM_DEPS_SPUTNIK = ('bleeding_edge/test/sputnik/sputniktests',
                         'http://sputniktests.googlecode.com/svn/trunk@94')

  # Pinned at revision 65044 to allow scons to be removed from repository.
  CUSTOM_DEPS_SCONS = ('third_party/scons',
                       config.Master.trunk_url +
                       '/src/third_party/scons@65044')

  CUSTOM_DEPS_VALGRIND = ('src/third_party/valgrind',
                          config.Master.trunk_url +
                          '/deps/third_party/valgrind/binaries')

  CUSTOM_DEPS_WIN7SDK = ('third_party/win7sdk',
                         config.Master.trunk_internal_url +
                         '/third_party/platformsdk_win7/files')

  CUSTOM_DEPS_MOZILLA = ('bleeding_edge/test/mozilla/data',
                          config.Master.trunk_url +
                          '/deps/third_party/mozilla-tests')

  def __init__(self, build_dir, target_platform=None):
    main = gclient_factory.GClientSolution(config.Master.v8_bleeding_edge)

    custom_deps_list = [main]

    gclient_factory.GClientFactory.__init__(self, build_dir, custom_deps_list,
                                            target_platform=target_platform)

  @staticmethod
  def _AddTests(factory_cmd_obj, tests, mode=None, factory_properties=None,
                target_arch=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    factory_properties = factory_properties or {}

    # Small helper function to check if we should run a test
    def R(test):
      return gclient_factory.ShouldRunTest(tests, test)

    f = factory_cmd_obj

    if R('presubmit'): f.AddPresubmitTest()
    if R('v8testing'): f.AddV8Testing()
    if R('v8_es5conform'): f.AddV8ES5Conform()
    if R('fuzz'): f.AddFuzzer()

    # Mozilla tests should be moved to v8 repo
    if R('mozilla'):
      f.AddV8Mozilla()

    if R('sputnik'): f.AddV8Sputnik()
    if target_arch == 'arm':
      if R('v8testing'):
        f.AddV8Testing(simulator='arm')
      if R('v8_es5conform'):
        f.AddV8ES5Conform(simulator='arm')
      if R('mozilla'):
        f.AddV8Mozilla(simulator='arm')
      if R('sputnik'):
        f.AddV8Sputnik(simulator='arm')


  def V8Factory(self, target='release', clobber=False, tests=None, mode=None,
                slave_type='BuilderTester', options=None, compile_timeout=1200,
                build_url=None, project=None, factory_properties=None,
                target_arch=None, crankshaft=False, shard_count=1,
                shard_run=1):
    tests = tests or []
    factory_properties = factory_properties or {}

    # Add scons which is not on a build slave by default
    self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_SCONS)

    # If we are on win32 add extra python executable
    if (self._target_platform == 'win32'):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_PYTHON)
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_WIN7SDK)

    if (gclient_factory.ShouldRunTest(tests, 'v8_es5conform')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_ES5CONFORM)

    if (gclient_factory.ShouldRunTest(tests, 'sputnik')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_SPUTNIK)

    if (gclient_factory.ShouldRunTest(tests, 'leak')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_VALGRIND)

    if (gclient_factory.ShouldRunTest(tests, 'mozilla')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_MOZILLA)

    if (gclient_factory.ShouldRunTest(tests, 'arm')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_MOZILLA)
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_SPUTNIK)
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_ES5CONFORM)

    factory = self.BuildFactory(target, clobber, tests, mode,
                                slave_type, options, compile_timeout, build_url,
                                project, factory_properties)

    # Get the factory command object to create new steps to the factory.
    # Note - we give '' as build_dir as we use our own build in test tools
    v8_cmd_obj = v8_commands.V8Commands(factory,
                                        target,
                                        '',
                                        self._target_platform,
                                        target_arch,
                                        crankshaft,
                                        shard_count,
                                        shard_run)
    if factory_properties.get('archive_build'):
      v8_cmd_obj.AddArchiveBuild(
          extra_archive_paths=factory_properties.get('extra_archive_paths'))

    if (slave_type == 'Tester'):
      v8_cmd_obj.AddMoveExtracted()

    # Add all the tests.
    self._AddTests(v8_cmd_obj, tests, mode, factory_properties)
    return factory

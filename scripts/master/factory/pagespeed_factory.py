# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the pagespeed master BuildFactory's.

Based on gclient_factory.py and adds pagespeed-specific steps."""

from master.factory import gclient_factory
from master.factory import pagespeed_commands

import config


class PageSpeedFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the pagespeed master.cfg file."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  def __init__(self, build_dir, target_platform=None):
    main = gclient_factory.GClientSolution(
        "http://page-speed.googlecode.com/svn/lib/trunk/src")

    gclient_factory.GClientFactory.__init__(self, build_dir, [main],
                                            target_platform=target_platform)

  def _AddTests(self, factory_cmd_obj, tests, mode=None,
                factory_properties=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    factory_properties = factory_properties or {}

    # This function is too crowded, try to simplify it a little.
    def R(test):
      return gclient_factory.ShouldRunTest(tests, test)
    f = factory_cmd_obj
    fp = factory_properties

    if R('unit'):           f.AddBasicGTestTestStep('pagespeed_test', fp)


  def PageSpeedFactory(self, identifier, target='Release', clobber=False,
                       tests=None, mode=None, slave_type='BuilderTester',
                       options=None, compile_timeout=1200, build_url=None,
                       project=None, factory_properties=None):
    factory_properties = factory_properties or {}
    tests = tests or []

    factory = self.BuildFactory(identifier, target, clobber, tests, mode,
                                slave_type, options, compile_timeout, build_url,
                                project, factory_properties)

    # Get the factory command object to create new steps to the factory.
    pagespeed_cmd_obj = pagespeed_commands.PageSpeedCommands(
        factory,
        identifier,
        target,
        self._build_dir,
        self._target_platform)

    # Add all the tests.
    self._AddTests(pagespeed_cmd_obj, tests, mode, factory_properties)

    return factory

  def FirefoxAddOnFactory(self, identifier, target='Release', clobber=False,
                       tests=None, mode=None, slave_type='BuilderTester',
                       options=None, compile_timeout=1200, build_url=None,
                       project=None, factory_properties=None):
    # For firefox addon we don't use the default DEPS file.
    self._solutions[0] = gclient_factory.GClientSolution(
        "http://page-speed.googlecode.com/svn/firefox_addon/trunk/src")
    return self.PageSpeedFactory(identifier, target, clobber, tests, mode,
                                 slave_type, options, compile_timeout, build_url,
                                 project, factory_properties)


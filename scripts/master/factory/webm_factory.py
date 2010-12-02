# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the webm master BuildFactory's.

Based on gclient_factory.py and adds webm-specific steps."""

from master.factory import gclient_factory
from master.factory import webm_commands
from master.factory.build_factory import BuildFactory

import config


class WebMFactory(object):
  """Encapsulates data and methods common to the webm master.cfg file."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  def __init__(self, build_dir, target_platform=None):
    self._build_dir = build_dir
    self._target_platform = target_platform or 'win32'

  def _AddTests(self, factory_cmd_obj, tests, mode=None,
                factory_properties=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    # TODO: Remove the following line once you've added tests.
    # pylint: disable=R0201,W0612
    factory_properties = factory_properties or {}

    # This function is too crowded, try to simplify it a little.
    def R(test):
      return gclient_factory.ShouldRunTest(tests, test)
    f = factory_cmd_obj
    fp = factory_properties

    # ADD TESTS HERE. Example:
    # if R('unit_tests'):  f.AddUnitTests()

  def WebMFactory(self, identifier, target='Release', clobber=False,
                       tests=None, mode=None, slave_type='BuilderTester',
                       options=None, compile_timeout=1200, build_url=None,
                       project=None, factory_properties=None):
    factory_properties = factory_properties or {}
    tests = tests or []

    factory = BuildFactory()

    # Get the factory command object to create new steps to the factory.
    webm_cmd_obj = webm_commands.WebMCommands(factory,
                                              identifier,
                                              target,
                                              self._build_dir,
                                              self._target_platform)

    # First kill any svn.exe tasks so we can update in peace, and
    # afterwards use the checked-out script to kill everything else.
    if self._target_platform == 'win32':
      webm_cmd_obj.AddSvnKillStep()
    webm_cmd_obj.AddUpdateScriptStep()
    # Once the script is updated, the zombie processes left by the previous
    # run can be killed.
    if self._target_platform == 'win32':
      webm_cmd_obj.AddTaskkillStep()

    # ADD UPDATE AND COMPILE STEP HERE.

    # Add all the tests.
    self._AddTests(webm_cmd_obj, tests, mode, factory_properties)

    return factory

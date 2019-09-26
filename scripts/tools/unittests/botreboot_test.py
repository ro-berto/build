#!/usr/bin/env vpython
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import subprocess
import sys
import unittest

import mock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURR_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(CURR_DIR, os.pardir, os.pardir)
BUILD_DIR = os.path.join(SCRIPTS_DIR, os.pardir)
SITE_CONFIG_DIR = os.path.join(BUILD_DIR, 'site_config')
DEPOT_TOOLS_DIR = os.path.join(BUILD_DIR, os.pardir, 'depot_tools')

import test_env
import slave.reboot_tools

# Trick reboot_tools to accept a dummy master config
sys.path.insert(0, SITE_CONFIG_DIR)
import config_bootstrap

class DummyMasterReboot(config_bootstrap.Master.Master1):
  project_name = 'Dummy Master Reboot'
  reboot_on_step_timeout = True


class DummyMasterNoReboot(config_bootstrap.Master.Master1):
  project_name = 'Dummy Master No Reboot'
  reboot_on_step_timeout = False

class DummyMasterDefault(config_bootstrap.Master.Master1):
  project_name = 'Dummy Master Default'

class SleepException(Exception):
  pass


def MockSleep(desired_sleep):
  raise SleepException


class BotRebootTest(unittest.TestCase):
  def setUp(self):
    super(BotRebootTest, self).setUp()
    self.log_messages = []
    self.subprocess_calls = []
    if hasattr(os.environ, 'TESTING_MASTER'):
      del os.environ['TESTING_MASTER']

    mocks = [
      mock.patch('slave.reboot_tools.Log', side_effect=self.MockLog),
      mock.patch('subprocess.call', side_effect=self.MockCall),
      mock.patch('slave.reboot_tools.Sleep', side_effect=MockSleep),
    ]
    for m in mocks:
      m.start()
      self.addCleanup(m.stop)

  def tearDown(self):
    if hasattr(os.environ, 'TESTING_MASTER'):
      del os.environ['TESTING_MASTER']
    super(BotRebootTest, self).tearDown()

  def MockLog(self, msg):
    self.log_messages.append(msg)

  def MockCall(self, args):
    self.subprocess_calls.append(args)

  def test_reboot(self):
    setattr(config_bootstrap.Master, 'active_master', DummyMasterReboot)
    # Run in test mode, don't actually reboot
    os.environ['TESTING_MASTER'] = 'DummyMasterReboot'
    slave.reboot_tools.Reboot()
    msg = 'Reboot: Testing mode enabled, skipping the actual reboot'
    self.assertIn(msg, self.log_messages)

  def test_no_record(self):
    setattr(config_bootstrap.Master, 'active_master', DummyMasterDefault)
    # Run in test mode, don't actually reboot
    os.environ['TESTING_MASTER'] = 'DummyMasterDefault'
    slave.reboot_tools.Reboot()
    msg = 'Reboot: Testing mode enabled, skipping the actual reboot'
    self.assertIn(msg, self.log_messages)

  def test_no_reboot(self):
    setattr(config_bootstrap.Master, 'active_master', DummyMasterNoReboot)
    # Run in test mode, don't actually reboot
    os.environ['TESTING_MASTER'] = 'DummyMasterNoReboot'
    slave.reboot_tools.Reboot()
    msg = 'Reboot: Testing mode enabled, skipping the actual reboot'
    self.assertNotIn(msg, self.log_messages)
    self.assertNotIn('Reboot: Issuing Reboot...', self.log_messages)

  def test_issue_reboot(self):
    setattr(config_bootstrap.Master, 'active_master', DummyMasterReboot)
    # Do NOT define TESTING_MASTER, we want to reach IssueReboot().
    # However, setup a backdoor to capture the shutdown command and
    # provide a quick exit from the infinite loop
    try:
      slave.reboot_tools.Reboot()
    except SleepException:
      pass
    calls_expected = [['sudo', 'shutdown', '-r', 'now']]
    self.assertIn('Reboot: Issuing Reboot...', self.log_messages)
    self.assertEqual(calls_expected, self.subprocess_calls)


if __name__ == '__main__':
  unittest.TestCase.maxDiff = None
  unittest.main()

#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

SWARM_BOOTSTRAP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'swarm_bootstrap')
sys.path.insert(0, SWARM_BOOTSTRAP_DIR)

import start_slave


class SwarmStartSlaveTest(unittest.TestCase):
  def setUp(self):
    # Ensure that none of the tests try to actually write files.
    self.old_write_to_json = start_slave.WriteJsonToFile
    start_slave.WriteJsonToFile = lambda _filepath, _data: True

  def tearDown(self):
    start_slave.WriteJsonToFile = self.old_write_to_json

  def test_dimensions(self):
    bits = start_slave.GetArchitectureSize()
    machine = os.uname()[4]

    actual = start_slave.GetChromiumDimensions('s33-c4', 'darwin', '10.8')
    expected = {'dimensions': {'bits': bits, 'machine': machine,
                               'os': ['Mac', 'Mac-10.8'], 'vlan': 'm4'},
                'tag': 's33-c4'}
    self.assertEqual(expected, actual)

    actual = start_slave.GetChromiumDimensions('vm1-m4', 'linux2', '12.04')
    expected = {'dimensions': {'bits': bits, 'machine': machine,
                               'os': ['Linux', 'Linux-12.04'], 'vlan': 'm4'},
                'tag': 'vm1-m4'}
    self.assertEqual(expected, actual)

    actual = start_slave.GetChromiumDimensions('vm1-m1', 'win32', '7')
    expected = {'dimensions': {'bits': bits, 'machine': machine,
                               'os': ['Windows', 'Windows-7'], 'vlan': 'm1'},
                'tag': 'vm1-m1'}
    self.assertEqual(expected, actual)

  def test_mac_mapping(self):
    self.assertEqual('10.7', start_slave.ConvertMacVersion('10.7.2'))
    self.assertEqual('10.8', start_slave.ConvertMacVersion('10.8.4'))
    self.assertEqual('10.9', start_slave.ConvertMacVersion('10.9'))

  def test_windows_mapping(self):
    self.assertEqual('5.1', start_slave.ConvertWindowsVersion('5.1.2505'))
    self.assertEqual('5.1',
                     start_slave.ConvertWindowsVersion('5.1.2600.2180'))
    self.assertEqual(
        '5.1',
        start_slave.ConvertWindowsVersion('CYGWIN_NT-5.1.2600'))

    self.assertEqual('6.0', start_slave.ConvertWindowsVersion('6.0.5048'))
    self.assertEqual(
        '6.0',
        start_slave.ConvertWindowsVersion('CYGWIN_NT-6.0.5048'))

    self.assertEqual('6.1',
                     start_slave.ConvertWindowsVersion('6.1.7600.16385'))
    self.assertEqual(
        '6.1',
        start_slave.ConvertWindowsVersion('CYGWIN_NT-6.1.7601'))

    self.assertEqual('6.2', start_slave.ConvertWindowsVersion('6.2.9200'))
    self.assertEqual(
        '6.2',
        start_slave.ConvertWindowsVersion('CYGWIN_NT-6.2.9200'))

  def test_main(self):  # pylint: disable=R0201
    # Make sure that main can run without crashing, because if it crash all
    # the swarm slaves will be unable to restart themselves and they'll need
    # to be manually reset.
    start_slave.main()


if __name__ == '__main__':
  unittest.TestCase.maxDiff = None
  unittest.main()

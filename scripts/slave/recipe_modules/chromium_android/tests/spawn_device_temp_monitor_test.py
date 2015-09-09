#!/usr/bin/env python
# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# For 'test_env'.
sys.path.insert(
    0, os.path.abspath(os.path.join(THIS_DIR, '..', '..', '..', 'unittests')))
# For 'spawn_device_temp_monitor.py'.
sys.path.insert(
    0, os.path.abspath(os.path.join(THIS_DIR, '..', 'resources')))

# Imported for side effects on sys.path.
import test_env
import mock

# In depot_tools/
from testing_support import auto_stub
import spawn_device_temp_monitor


class SimulatedSigterm(Exception):
  pass


class MainFuncTest(auto_stub.TestCase):
  def setUp(self):
    # Collect calls to 'subprocess.Popen', which calls send_ts_mon_values.py.
    self.send_ts_mon_call = []
    def mocked_ts_mon_calls(args):
      self.send_ts_mon_call = args
    self.mock(
        spawn_device_temp_monitor.subprocess,
        'Popen',
        mocked_ts_mon_calls)

    # Make sleep throw an exception to simulate a sigterm
    # and break out of loop.
    def mocked_sleep_call(duration):
      self.assertEquals(60, duration)
      raise SimulatedSigterm('simulated sigterm')
    self.mock(
        spawn_device_temp_monitor.time,
        'sleep',
        mocked_sleep_call)

  def test_main_responsive_device(self):
    # Collect calls to 'subprocess.check_output', which calls adb, and
    # simulate a responsive device.
    adb_calls = []
    def mocked_adb_calls(args):
      adb_calls.append(args)
      if args[4].startswith('grep'):
        return "some_thermal_file_name"
      elif args[4].startswith('cat'):
        return "123"
      elif args[4].startswith('dumpsys'):
        return "temperature: 456"
      else:
        self.fail('Unexpected adb command: %s' % (' '.join(args)))

    self.mock(
        spawn_device_temp_monitor.subprocess,
        'check_output',
        mocked_adb_calls)
    try:
      spawn_device_temp_monitor.main(
          '/some/adb/path',
          '["device_serial_1"]',
          'some_slave_name')
    except SimulatedSigterm:
      pass

    # Should build args to send_ts_mon_values correctly.
    expected_cmd = [spawn_device_temp_monitor._RUN_PY,
        'infra.tools.send_ts_mon_values',
        '--float',
        '{"slave": "some_slave_name", "name": "dev/cpu/temperature", '
        '"value": 123, "device_id": "device_serial_1"}',
        '--float',
        '{"slave": "some_slave_name", "name": "dev/battery/temperature", '
        '"value": 456, "device_id": "device_serial_1"}']
    self.assertEquals(expected_cmd, self.send_ts_mon_call)
  
  def test_main_unresponsive_device(self):
    # Collect calls to 'subprocess.check_output', which calls adb, and
    # simulate an unresponsive device.
    adb_calls = []
    def mocked_adb_calls(args):
      adb_calls.append(args)
      raise subprocess.CalledProcessError

    self.mock(
        spawn_device_temp_monitor.subprocess,
        'check_output',
        mocked_adb_calls)
    try:
      spawn_device_temp_monitor.main(
          '/some/adb/path',
          '["device_serial_1"]',
          'some_slave_name')
    except SimulatedSigterm:
      pass

    # Should build args to send_ts_mon_values without any metrics.
    self.assertEquals(2, len(self.send_ts_mon_call))
    self.assertEquals(
        spawn_device_temp_monitor._RUN_PY,
        self.send_ts_mon_call[0])
    self.assertEquals(
        'infra.tools.send_ts_mon_values',
        self.send_ts_mon_call[1])


if __name__ == '__main__':
  unittest.main()

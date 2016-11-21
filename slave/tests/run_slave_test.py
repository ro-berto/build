#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Starts run_slave and verify if it starts successfully.
"""

import mock
import os
import re
import runpy
import subprocess
import sys
import unittest


RUN_SLAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.append(RUN_SLAVE_PATH)

import run_slave

# import twisted to mock run()
_, tw_ver = run_slave.GetThirdPartyVersions(None)
sys.path.append(os.path.join(RUN_SLAVE_PATH, 'third_party', tw_ver))
import twisted.scripts.twistd


class ExecvExecuted(Exception):
  # This exception is raised within a mocked os.execv() so that
  # the execution flow gets interrupted.
  pass


def _GetCallArgumentFromMock(mock_call, position, keyword=None):
  args, kwargs = mock_call.call_args
  return kwargs[keyword] if keyword and keyword in kwargs else args[position]


class RunSlaveTest(unittest.TestCase):
  @mock.patch('subprocess.call')
  @mock.patch('os.execv', mock.Mock(side_effect=ExecvExecuted))
  def test_run_slave_restart_after_gclient_sync(self, subprocess_call):
    """Tests if run_slave restarts itself after gclient sync."""
    with self.assertRaises(ExecvExecuted):
      runpy.run_module("run_slave", run_name="__main__", alter_sys=True)

    # verify that gclient sync has been executed
    self.assertTrue(subprocess_call.called)
    call_cmd_args = _GetCallArgumentFromMock(subprocess_call, 0, 'args')
    self.assertEqual(call_cmd_args[0], run_slave.GetGClientPath())
    self.assertEqual(call_cmd_args[1], 'sync')

    # verify that run_slave.py was execv()-ed with --no-gclient-sync
    run_slave_py_path = re.sub(
        r'pyc$', 'py', os.path.abspath(run_slave.__file__))

    execv_cmd_args = _GetCallArgumentFromMock(os.execv, 1, 'args')
    self.assertIn(run_slave_py_path, execv_cmd_args[:2])
    self.assertIn('--no-gclient-sync', execv_cmd_args[1:])

  @mock.patch('subprocess.call')
  @mock.patch('subprocess.check_call')
  @mock.patch('subprocess.check_output')
  @mock.patch('twisted.scripts.twistd.run')
  @mock.patch('sys.argv', [run_slave.__file__, '--no-gclient-sync'])
  def test_run_slave_with_no_gclient_sync(self, twistd_run,
                                          subprocess_check_output,
                                          subprocess_check_call,
                                          subprocess_call):
    """Tests if twistd.run() gets invoked when --no-gclient-sync is given."""
    os.environ['TESTING_MASTER'] = 'Master1'
    os.environ['TESTING_SLAVE'] = 'Slave1'
    runpy.run_module("run_slave", run_name="__main__", alter_sys=True)

    gclient_path = run_slave.GetGClientPath()
    for mock_call in (subprocess_call, subprocess_check_call,
                      subprocess_check_output):
      if mock_call.called:
        cmd_args = _GetCallArgumentFromMock(mock_call, 0, 'args')

        # verify that gclient with sync option has not been called within
        # run_slave.
        if gclient_path == cmd_args[0]:
          self.assertNotEqual(cmd_args[1], 'sync')

    self.assertTrue(twistd_run.called)


if __name__ == '__main__':
  unittest.main()

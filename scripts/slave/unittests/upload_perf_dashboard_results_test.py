#!/usr/bin/env vpython
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test cases for upload_perf_dashboard_results_test.py"""

import unittest
import tempfile

import test_env  # pylint: disable=W0403,W0611

from common import chromium_utils
from slave import upload_perf_dashboard_results

import mock

class UploadPerfDashboardResultsTest(unittest.TestCase):
  """Tests related to functions which retrieve perfmastername."""

  def setUp(self):
    super(UploadPerfDashboardResultsTest, self).setUp()
    self.maxDiff = None
    self.parser = upload_perf_dashboard_results._CreateParser()
    gam = mock.patch('common.chromium_utils.GetActiveMaster',
                     new=lambda: 'ChromiumPerf')
    gam.start()
    self.addCleanup(gam.stop)

  def GetPerfDashboardMachineGroup(self, options):
    return upload_perf_dashboard_results._GetMachineGroup(options)

  def testGetMasterName_Buildbot_PerfDashboardMasterNameNotSet(self):
    options, _ = self.parser.parse_args([])
    self.assertEquals(
      'ChromiumPerf', self.GetPerfDashboardMachineGroup(options))

  def testGetMasterName_Buildbot_PerfDashboardMasterNameSet(self):
    options, _ = self.parser.parse_args(
        ['--perf-dashboard-machine-group', 'sensei'])
    self.assertEquals(
      'ChromiumPerf', self.GetPerfDashboardMachineGroup(options))

  def testGetMasterName_LUCI_PerfDashboardMasterNameNotSet(self):
    options, _ = self.parser.parse_args(['--is-luci-builder'])

    with self.assertRaises(ValueError):
      self.GetPerfDashboardMachineGroup(options)

  def testGetMasterName_LUCI_PerfDashboardMasterNameSet(self):
    options, _ = self.parser.parse_args(
        ['--is-luci-builder', '--perf-dashboard-machine-group', 'Yoda'])

    self.assertEquals('Yoda', self.GetPerfDashboardMachineGroup(options))


if __name__ == '__main__':
  unittest.main()

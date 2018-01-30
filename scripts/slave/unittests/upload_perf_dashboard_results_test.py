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
from testing_support.super_mox import mox


class UploadPerfDashboardResultsTest(unittest.TestCase):
  """Tests related to functions which retrieve perfmastername."""

  def setUp(self):
    super(UploadPerfDashboardResultsTest, self).setUp()
    self.mox = mox.Mox()
    self.maxDiff = None
    self.parser = upload_perf_dashboard_results._CreateParser()

  def tearDown(self):
    self.mox.UnsetStubs()

  def GetPerfDashboardMasterName(self, options):
    return upload_perf_dashboard_results._GetMasterName(options)

  def testGetMasterName_Buildbot_PerfDashboardMasterNameNotSet(self):
    self.mox.StubOutWithMock(chromium_utils, 'GetActiveMaster')
    chromium_utils.GetActiveMaster().AndReturn('ChromiumPerf')
    self.mox.ReplayAll()

    options, _ = self.parser.parse_args([])
    self.assertEquals('ChromiumPerf', self.GetPerfDashboardMasterName(options))

  def testGetMasterName_Buildbot_PerfDashboardMasterNameSet(self):
    self.mox.StubOutWithMock(chromium_utils, 'GetActiveMaster')
    chromium_utils.GetActiveMaster().AndReturn('ChromiumPerf')
    self.mox.ReplayAll()

    options, _ = self.parser.parse_args(
        ['--perf-dashboard-mastername', 'sensei'])
    self.assertEquals('ChromiumPerf', self.GetPerfDashboardMasterName(options))

  def testGetMasterName_LUCI_PerfDashboardMasterNameNotSet(self):
    self.mox.StubOutWithMock(chromium_utils, 'GetActiveMaster')
    chromium_utils.GetActiveMaster().AndReturn('ChromiumPerf')
    self.mox.ReplayAll()

    options, _ = self.parser.parse_args(['--is-luci-builder'])

    with self.assertRaises(ValueError):
      self.GetPerfDashboardMasterName(options)

  def testGetMasterName_LUCI_PerfDashboardMasterNameSet(self):
    self.mox.StubOutWithMock(chromium_utils, 'GetActiveMaster')
    chromium_utils.GetActiveMaster().AndReturn('ChromiumPerf')
    self.mox.ReplayAll()

    options, _ = self.parser.parse_args(
        ['--is-luci-builder', '--perf-dashboard-mastername', 'Yoda'])

    self.assertEquals('Yoda', self.GetPerfDashboardMasterName(options))


if __name__ == '__main__':
  unittest.main()

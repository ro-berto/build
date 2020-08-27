#!/usr/bin/env vpython
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test cases for upload_perf_dashboard_results_test.py"""

import os
import sys
import tempfile
import unittest

import mock

import test_env  # pylint: disable=relative-import

_SCRIPT_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(_SCRIPT_DIR, os.pardir)))

from common import chromium_utils
import upload_perf_dashboard_results


class UploadPerfDashboardResultsTest(unittest.TestCase):
  """Tests related to functions which retrieve perfmastername."""

  def setUp(self):
    super(UploadPerfDashboardResultsTest, self).setUp()
    self.maxDiff = None
    self.parser = upload_perf_dashboard_results._CreateParser()

  def GetPerfDashboardMachineGroup(self, options):
    return upload_perf_dashboard_results._GetMachineGroup(options)

  def testGetMasterName_LUCI_PerfDashboardMasterNameNotSet(self):
    options, _ = self.parser.parse_args(['--is-luci-builder'])

    with self.assertRaises(ValueError):
      self.GetPerfDashboardMachineGroup(options)

  def testGetMasterName_LUCI_PerfDashboardMasterNameSet(self):
    options, _ = self.parser.parse_args([
        '--is-luci-builder', '--perf-dashboard-machine-group', 'Yoda'
    ])

    self.assertEquals('Yoda', self.GetPerfDashboardMachineGroup(options))


if __name__ == '__main__':
  unittest.main()

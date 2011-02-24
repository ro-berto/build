#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for chromium_commands testcases."""

import unittest

from master.factory.chromium_commands import ChromiumCommands
from master.factory.commands import CreatePerformanceStepClass
from master.log_parser import process_log


class ChromiumCommandsTest(unittest.TestCase):

  def setUp(self):
    self.cmd = ChromiumCommands()
    self.log_processor_class = process_log.PerformanceLogProcessor
    self.report_link = 'http://localhost/report.html'
    self.output_dir = 'output-dir'

  def testCreatePerformanceStepClass(self):
    performanceStepClass = CreatePerformanceStepClass(
        self.log_processor_class, self.report_link, self.output_dir)
    performanceStep = performanceStepClass() # initialize
    self.assert_(performanceStep._log_processor)
    log_processor = performanceStep._log_processor
    self.assertEqual(self.report_link, log_processor._report_link)
    self.assertEqual(self.output_dir, log_processor._output_dir)

  def testCreatePerformanceStepClassWithMissingReportLinkArguments(self):
    performanceStepClass = CreatePerformanceStepClass(self.log_processor_class)
    performanceStep = performanceStepClass() # initialize
    self.assert_(performanceStep._log_processor)
    log_processor = performanceStep._log_processor
    self.assert_(not log_processor._report_link)
    self.assert_(log_processor._output_dir)

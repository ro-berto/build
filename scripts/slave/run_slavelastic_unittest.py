#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'site_config'))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

import slave.run_slavelastic as slavelastic


class TestSummaryTest(unittest.TestCase):
  def test_correct_output(self):
    summary_output = [
        ('[  PASSED  ] 10 tests.\n'
         'YOU HAVE 1 DISABLED TESTS\n'
         'YOU HAVE 1 test with ignored failures (FAILS prefix)'),
        ('[  PASSED  ] 10 tests\n'
         '[  FAILED  ] 1 test, listed below:\n'
         '[  FAILED  ] ObserverListThreadSafeTest.RemoveObserver\n'
         '1 FAILED TEST\n'
         'YOU HAVE 2 DISABLED TESTS\n'
         'YOU HAVE 2 test with ignored failures (FAILS prefix)\n')]

    expected_output = ['[  PASSED  ] 20 tests.',
                       '[  FAILED  ] failed tests listed below:',
                       '[  FAILED  ] ObserverListThreadSafeTest.RemoveObserver',
                       '1 FAILED TESTS',
                       '3 DISABLED TESTS',
                       '3 tests with ignored failures (FAILS prefix)']

    summary = slavelastic.TestSummary()

    for data in summary_output:
      summary.AddSummaryData(data)

    self.assertEquals(expected_output, summary.Output())

  def test_correct_all_pass(self):
    summary_output = [
        ('[  PASSED  ] 10 tests.'),
        ('[  PASSED  ] 10 tests')]

    expected_output = ['[  PASSED  ] 20 tests.']

    summary = slavelastic.TestSummary()

    for data in summary_output:
      summary.AddSummaryData(data)

    self.assertEquals(expected_output, summary.Output())


if __name__ == '__main__':
  unittest.main()

#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import test_env  # pylint: disable=W0403,W0611

import StringIO
import unittest

from testing_support.super_mox import mox
from testing_support.super_mox import SuperMoxTestBase

import slave.get_swarm_results as swarm_results


class TestRunSummaryTest(unittest.TestCase):
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

    summary = swarm_results.TestRunSummary()

    for data in summary_output:
      summary.AddSummaryData(data)

    self.assertEquals(expected_output, summary.Output())

  def test_correct_all_pass(self):
    summary_output = [
        ('[  PASSED  ] 10 tests.'),
        ('[  PASSED  ] 10 tests')]

    expected_output = ['[  PASSED  ] 20 tests.']

    summary = swarm_results.TestRunSummary()

    for data in summary_output:
      summary.AddSummaryData(data)

    self.assertEquals(expected_output, summary.Output())

  def test_test_run_output(self):
    full_output = ('[==========] Running 1 tests from results test run.\n'
                   '[ RUN      ] results.Run Test\n'
                   'DONE\n'
                   '[       OK ] results.Run Test (10 ms)\n\n'
                   '[----------] results summary\n'
                   '[==========] 1 tests ran. (10 ms total)\n'
                   '[  PASSED  ] 1 tests.\n'
                   '[  FAILED  ] 0 tests\n\n'
                   ' 0 FAILED TESTS')

    cleaned_output = swarm_results.TestRunOutput(full_output)

    self.assertEquals('DONE\n', cleaned_output)


class GetTestKetsTest(SuperMoxTestBase):
  def test_no_keys(self):
    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')
    response = StringIO.StringIO('No matching Test Cases')
    swarm_results.urllib2.urlopen(mox.IgnoreArg()).AndReturn(
        response)
    self.mox.ReplayAll()

    self.assertEqual([], swarm_results.GetTestKeys('http://host:9001',
                                                   'my_test'))
    self.checkstdout('Error: Unable to find any tests with the name, '
                     'my_test, on swarm server\n')

    self.mox.VerifyAll()

  def test_find_keys(self):
    keys = ['key_1', 'key_2']

    self.mox.StubOutWithMock(swarm_results.urllib2, 'urlopen')
    response = StringIO.StringIO('\n'.join(keys))
    swarm_results.urllib2.urlopen(mox.IgnoreArg()).AndReturn(
        response)
    self.mox.ReplayAll()

    self.assertEqual(keys,
                     swarm_results.GetTestKeys('http://host:9001', 'my_test'))

    self.mox.VerifyAll()


if __name__ == '__main__':
  unittest.main()

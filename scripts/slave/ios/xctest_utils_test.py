#!/usr/bin/env vpython
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for classes in xctest_utils.py."""

# pylint: disable=relative-import
import environment_setup

import os
import tempfile
import unittest

import xctest_utils


TAP_ERRORS = ('Exception: NoMatchingElementException'
              'Reason: Action \'Tap\' was not performed because no UI element '
              'matching accessibilityLabel("Menu")  was found')

RELOAD_ERRORS = ('Exception: ActionFailedException'
                 'Fail to reload')

TIMEOUT_ERRORS = 'Exception: Timeout'

FAILING_TESTS_EXPECTED = ['ChromeSmokeTestCase.testTapToolsMenu',
                          'ChromeSmokeTestCase.testReload',
                          'ChromeSmokeTestCase.testTimeout']

TEST_SUCCEEDED_DATA = """
Test Case '-[webShellTest testOne]' started.
Test Case '-[webShellTest testOne]' started.
ios_web_shell_test_host: Adjusting repeatCount to 8.375000 for animation
ios_web_shell_test_host: Adjusting repeatCount to 8.375000 for animation
ios_web_shell_test_host: Adjusting repeatCount to 8.375000 for animation
ios_web_shell_test_host: Adjusting repeatCount to 8.375000 for animation
ios_web_shell_test_host: Adjusting repeatCount to 8.375000 for animation
ios_web_shell_test_host: Adjusting repeatCount to 8.375000 for animation
ios_web_shell_test_host: Adjusting repeatCount to 8.375000 for animation
ios_web_shell_test_host: Adjusting repeatCount to 8.375000 for animation
Test Case '-[webShellTest testOne]' passed (0.381 seconds).
Test Suite 'webShellTest' passed at 2016-05-04 18:05:01.914.
 Executed 1 test, with 0 failures (0 unexpected) in 0.381 (2.597) seconds
 Test Suite 'ios_web_shell_test_host.app' passed at 2016-05-04 18:05:01.914.
 Executed 1 test, with 0 failures (0 unexpected) in 0.381 (2.598) seconds
 Test Suite 'All tests' passed at 2016-05-04 18:05:01.915.
 Executed 1 test, with 0 failures (0 unexpected) in 0.381 (2.600) seconds
 xcodebuild returned 0
** TEST SUCCEEDED **
"""

TEST_MIXED_DATA = ("""
Test Suite 'All tests' started at 2016-05-04 17:55:26.353
Test Suite 'chrome_eg_smoke_test_host.app' started at 2016-05-04 17:55:26.354
Test Suite 'ChromeSmokeTestCase' started at 2016-05-04 17:55:26.354
Test Case '-[ChromeSmokeTestCase testTabs]' started.
Test Case '-[ChromeSmokeTestCase testTabs]' passed (2.203 seconds).
Test Case '-[ChromeSmokeTestCase testTapToolsMenu]' started.
%(tap_errors)s
Test Case '-[ChromeSmokeTestCase testTapToolsMenu]' failed (0.033 seconds).
Test Suite 'ChromeSmokeTestCase' failed at 2016-05-04 17:55:28.592.
Test Case '-[ChromeSmokeTestCase testReload]' started.
%(reload_errors)s
Test Case '-[ChromeSmokeTestCase testReload]' failed (1.1 seconds).
Test Case '-[ChromeSmokeTestCase testTimeout]' started.
%(timeout_errors)s
 Executed 4 tests, with 3 failure (3 unexpected) in 2.236 (2.238) seconds
 Test Suite 'chrome_eg_smoke_test_host.app' failed at 2016-05-04 17:55:28.593.
 Executed 4 tests, with 2 failure (3 unexpected) in 2.236 (2.239) seconds
 Test Suite 'All tests' failed at 2016-05-04 17:55:28.593.
 Executed 4 tests, with 2 failure (3 unexpected) in 2.236 (2.241) seconds
 ** TEST FAILED **
 xcodebuild returned 65
  """ % {'tap_errors': TAP_ERRORS,
         'reload_errors': RELOAD_ERRORS,
         'timeout_errors': TIMEOUT_ERRORS})


class TestXCTestLogParserTests(unittest.TestCase):
  """Test xctest log parser, xctest_utils.py."""

  def testXCTestLogParserStdout(self):
    parser = xctest_utils.XCTestLogParser()
    for line in TEST_SUCCEEDED_DATA.splitlines():
      parser.ProcessLine(line)

    self.assertEqual(0, len(parser.ParsingErrors()))
    self.assertFalse(parser.RunningTests())
    self.assertFalse(parser.FailedTests())
    self.assertEqual(['webShellTest.testOne'], parser.PassedTests())
    self.assertEqual(['SUCCESS'], parser.TriesForTest('webShellTest.testOne'))
    self.assertTrue(parser.CompletedWithoutFailure())

    parser = xctest_utils.XCTestLogParser()
    for line in TEST_MIXED_DATA.splitlines():
      parser.ProcessLine(line)

    self.assertEqual(sorted(FAILING_TESTS_EXPECTED),
                 parser.FailedTests(True, True))
    test_name = 'ChromeSmokeTestCase.testTapToolsMenu'
    self.assertEqual('\n'.join(['%s: ' % test_name, TAP_ERRORS]),
                     '\n'.join(parser.FailureDescription(test_name)))
    self.assertEqual(['FAILURE'], parser.TriesForTest(test_name))

    test_name = 'ChromeSmokeTestCase.testReload'
    self.assertEqual('\n'.join(['%s: ' % test_name, RELOAD_ERRORS]),
                     '\n'.join(parser.FailureDescription(test_name)))
    self.assertEqual(['FAILURE'], parser.TriesForTest(test_name))


if __name__ == '__main__':
  unittest.main()

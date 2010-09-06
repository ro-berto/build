#!/usr/bin/python
# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for classes in gtest_command.py."""

import unittest

from log_parser import gtest_command

FAILURES = ['NavigationControllerTest.Reload',
            'NavigationControllerTest.Back',
            'BadTest.TimesOut',
            'SomeOtherTest.SwitchTypes']

RELOAD_ERRORS = """
C:\b\slave\chrome-release-snappy\build\chrome\browser\navigation_controller_unittest.cc:381: Failure
Value of: -1
Expected: contents->controller()->GetPendingEntryIndex()
Which is: 0

"""

BACK_ERRORS = """
C:\b\slave\chrome-release-snappy\build\chrome\browser\navigation_controller_unittest.cc:439: Failure
Value of: -1
Expected: contents->controller()->GetPendingEntryIndex()
Which is: 0

"""

SWITCH_ERRORS = """
C:\b\slave\chrome-release-snappy\build\chrome\browser\navigation_controller_unittest.cc:615: Failure
Value of: -1
Expected: contents->controller()->GetPendingEntryIndex()
Which is: 0

C:\b\slave\chrome-release-snappy\build\chrome\browser\navigation_controller_unittest.cc:617: Failure
Value of: contents->controller()->GetPendingEntry()
  Actual: true
Expected: false

"""

TEST_DATA = """
[==========] Running 7 tests from 3 test cases.
[----------] Global test environment set-up.
[----------] 1 test from HunspellTest
[ RUN      ] HunspellTest.All
[       OK ] HunspellTest.All (62 ms)
[----------] 1 test from HunspellTest (62 ms total)

[----------] 4 tests from NavigationControllerTest
[ RUN      ] NavigationControllerTest.Defaults
[       OK ] NavigationControllerTest.Defaults (48 ms)
[ RUN      ] NavigationControllerTest.Reload
%(reload_errors)s
[  FAILED  ] NavigationControllerTest.Reload (2 ms)
[ RUN      ] NavigationControllerTest.Reload_GeneratesNewPage
[       OK ] NavigationControllerTest.Reload_GeneratesNewPage (22 ms)
[ RUN      ] NavigationControllerTest.Back
%(back_errors)s
[  FAILED  ] NavigationControllerTest.Back (2 ms)
[----------] 4 tests from NavigationControllerTest (74 ms total)

  YOU HAVE 2 FLAKY TESTS

[----------] 1 test from BadTest
[ RUN      ] BadTest.TimesOut
[61613:263:0531/042613:2887943745568888:ERROR:/b/slave/chromium-rel-mac-builder/build/src/chrome/browser/extensions/extension_error_reporter.cc(56)] Extension error: Could not load extension from 'extensions/api_test/geolocation/no_permission'. Manifest file is missing or unreadable.
[0531/042642:ERROR:/b/slave/chromium-rel-mac-builder/build/src/chrome/test/test_launcher/out_of_proc_test_runner.cc(79)] Test timeout (30000 ms) exceeded for BadTest.TimesOut
Handling SIGTERM.
Successfully wrote to shutdown pipe, resetting signal handler.
[61613:19971:0531/042642:2887973024284693:INFO:/b/slave/chromium-rel-mac-builder/build/src/chrome/browser/browser_main.cc(285)] Handling shutdown for signal 15.

[----------] 1 test from SomeOtherTest
[ RUN      ] SomeOtherTest.SwitchTypes
%(switch_errors)s
[  FAILED  ] SomeOtherTest.SwitchTypes (40 ms)
[ RUN      ] SomeOtherTest.Foo
[       OK ] SomeOtherTest.Foo (20 ms)
[----------] 2 tests from SomeOtherTest (60 ms total)

[----------] Global test environment tear-down
[==========] 7 tests from 3 test cases ran. (3750 ms total)
[  PASSED  ] 4 tests.
[  FAILED  ] 3 tests, listed below:
[  FAILED  ] NavigationControllerTest.Reload
[  FAILED  ] NavigationControllerTest.Back
[  FAILED  ] SomeOtherTest.SwitchTypes

 1 FAILED TEST
  YOU HAVE 10 DISABLED TESTS

  YOU HAVE 2 FLAKY TESTS

program finished with exit code 1
""" % {'reload_errors': RELOAD_ERRORS,
       'back_errors'  : BACK_ERRORS,
       'switch_errors': SWITCH_ERRORS}

TEST_DATA_CRASH = """
[==========] Running 7 tests from 3 test cases.
[----------] Global test environment set-up.
[----------] 1 test from HunspellTest
[ RUN      ] HunspellTest.Crashes
Oops, this test crashed!
"""

class TestObserverTests(unittest.TestCase):
  def testLogLineObserver(self):
    observer = gtest_command.TestObserver()
    for line in TEST_DATA.splitlines():
      observer.outLineReceived(line)

    self.assertFalse(observer.internal_error)
    self.assertFalse(observer.RunningTests())
    self.assertEqual(sorted(FAILURES), sorted(observer.FailedTests()))
    self.assertEqual(10, observer.disabled_tests)
    self.assertEquals(2, observer.flaky_tests)

    test_name = 'NavigationControllerTest.Reload'
    self.assertEqual('\n'.join(['%s: ' % test_name, RELOAD_ERRORS]),
                     '\n'.join(observer.FailureDescription(test_name)))

    test_name = 'NavigationControllerTest.Back'
    self.assertEqual('\n'.join(['%s: ' % test_name, BACK_ERRORS]),
                     '\n'.join(observer.FailureDescription(test_name)))

    test_name = 'SomeOtherTest.SwitchTypes'
    self.assertEqual('\n'.join(['%s: ' % test_name, SWITCH_ERRORS]),
                     '\n'.join(observer.FailureDescription(test_name)))

    test_name = 'BadTest.TimesOut'
    self.assertEqual('\n'.join(['%s: ' % test_name, 'Killed (timed out).']),
                     '\n'.join(observer.FailureDescription(test_name)))

    observer = gtest_command.TestObserver()
    for line in TEST_DATA_CRASH.splitlines():
      observer.outLineReceived(line)

    self.assertFalse(observer.internal_error)
    self.assertTrue(observer.RunningTests())
    self.assertEqual(['HunspellTest.Crashes'], observer.FailedTests())
    self.assertEqual(0, observer.disabled_tests)
    self.assertEquals(0, observer.flaky_tests)

    test_name = 'HunspellTest.Crashes'
    self.assertEqual('\n'.join(['%s: ' % test_name, 'Did not complete.']),
                     '\n'.join(observer.FailureDescription(test_name)))


if __name__ == '__main__':
  unittest.main()

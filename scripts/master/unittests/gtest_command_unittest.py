#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for classes in gtest_command.py."""

import unittest

from log_parser import gtest_command

FAILURES = ['NavigationControllerTest.Reload',
            'NavigationControllerTest/SpdyNetworkTransTest.Constructor/0',
            'BadTest.TimesOut',
            'MoreBadTest.TimesOutAndFails',
            'SomeOtherTest.SwitchTypes']

FAILS_FAILURES = ['SomeOtherTest.FAILS_Bar']
FLAKY_FAILURES = ['SomeOtherTest.FLAKY_Baz']

TIMEOUT_MESSAGE = 'Killed (timed out).'

RELOAD_ERRORS = """
C:\b\slave\chrome-release-snappy\build\chrome\browser\navigation_controller_unittest.cc:381: Failure
Value of: -1
Expected: contents->controller()->GetPendingEntryIndex()
Which is: 0

"""

SPDY_ERRORS = """
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

TIMEOUT_ERRORS = """
[61613:263:0531/042613:2887943745568888:ERROR:/b/slave/chromium-rel-mac-builder/build/src/chrome/browser/extensions/extension_error_reporter.cc(56)] Extension error: Could not load extension from 'extensions/api_test/geolocation/no_permission'. Manifest file is missing or unreadable.
"""

MOREBAD_ERRORS = """
Value of: entry->page_type()
  Actual: 2
Expected: NavigationEntry::NORMAL_PAGE
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
[ RUN      ] NavigationControllerTest/SpdyNetworkTransTest.Constructor/0
%(spdy_errors)s
[  FAILED  ] NavigationControllerTest/SpdyNetworkTransTest.Constructor/0 (2 ms)
[----------] 4 tests from NavigationControllerTest (74 ms total)

  YOU HAVE 2 FLAKY TESTS

[----------] 1 test from BadTest
[ RUN      ] BadTest.TimesOut
%(timeout_errors)s
[0531/042642:ERROR:/b/slave/chromium-rel-mac-builder/build/src/chrome/test/test_launcher/out_of_proc_test_runner.cc(79)] Test timeout (30000 ms) exceeded for BadTest.TimesOut
Handling SIGTERM.
Successfully wrote to shutdown pipe, resetting signal handler.
[61613:19971:0531/042642:2887973024284693:INFO:/b/slave/chromium-rel-mac-builder/build/src/chrome/browser/browser_main.cc(285)] Handling shutdown for signal 15.

[----------] 1 test from MoreBadTest
[ RUN      ] MoreBadTest.TimesOutAndFails
%(morebad_errors)s
[0531/042642:ERROR:/b/slave/chromium-rel-mac-builder/build/src/chrome/test/test_launcher/out_of_proc_test_runner.cc(79)] Test timeout (30000 ms) exceeded for MoreBadTest.TimesOutAndFails
Handling SIGTERM.
Successfully wrote to shutdown pipe, resetting signal handler.
[  FAILED  ] MoreBadTest.TimesOutAndFails (31000 ms)

[----------] 4 tests from SomeOtherTest
[ RUN      ] SomeOtherTest.SwitchTypes
%(switch_errors)s
[  FAILED  ] SomeOtherTest.SwitchTypes (40 ms)
[ RUN      ] SomeOtherTest.Foo
[       OK ] SomeOtherTest.Foo (20 ms)
[ RUN      ] SomeOtherTest.FAILS_Bar
Some error message for a failing test.
[  FAILED  ] SomeOtherTest.FAILS_Bar (40 ms)
[ RUN      ] SomeOtherTest.FLAKY_Baz
Some error message for a flaky test.
[  FAILED  ] SomeOtherTest.FLAKY_Baz (40 ms)
[----------] 2 tests from SomeOtherTest (60 ms total)

[----------] Global test environment tear-down
[==========] 7 tests from 3 test cases ran. (3750 ms total)
[  PASSED  ] 4 tests.
[  FAILED  ] 3 tests, listed below:
[  FAILED  ] NavigationControllerTest.Reload
[  FAILED  ] NavigationControllerTest/SpdyNetworkTransTest.Constructor/0
[  FAILED  ] SomeOtherTest.SwitchTypes

 1 FAILED TEST
  YOU HAVE 10 DISABLED TESTS

  YOU HAVE 2 FLAKY TESTS

program finished with exit code 1
""" % {'reload_errors' : RELOAD_ERRORS,
       'spdy_errors'   : SPDY_ERRORS,
       'switch_errors' : SWITCH_ERRORS,
       'timeout_errors': TIMEOUT_ERRORS,
       'morebad_errors': MOREBAD_ERRORS}

TEST_DATA_CRASH = """
[==========] Running 7 tests from 3 test cases.
[----------] Global test environment set-up.
[----------] 1 test from HunspellTest
[ RUN      ] HunspellTest.Crashes
Oops, this test crashed!
"""

VALGRIND_HASH = 'B254345E4D3B6A00'

VALGRIND_SUPPRESSION = """Suppression (error hash=#%(hash)s#):
{
   <insert_a_suppression_name_here>
   Memcheck:Leak
   fun:_Znw*
   fun:_ZN31NavigationControllerTest_Reload8TestBodyEv
}""" % {'hash' : VALGRIND_HASH}

TEST_DATA_VALGRIND = """
[==========] Running 5 tests from 2 test cases.
[----------] Global test environment set-up.
[----------] 1 test from HunspellTest
[ RUN      ] HunspellTest.All
[       OK ] HunspellTest.All (62 ms)
[----------] 1 test from HunspellTest (62 ms total)

[----------] 4 tests from NavigationControllerTest
[ RUN      ] NavigationControllerTest.Defaults
[       OK ] NavigationControllerTest.Defaults (48 ms)
[ RUN      ] NavigationControllerTest.Reload
[       OK ] NavigationControllerTest.Reload (2 ms)
[ RUN      ] NavigationControllerTest.Reload_GeneratesNewPage
[       OK ] NavigationControllerTest.Reload_GeneratesNewPage (22 ms)
[ RUN      ] NavigationControllerTest/SpdyNetworkTransTest.Constructor/0
[       OK ] NavigationControllerTest/SpdyNetworkTransTest.Constructor/0 (2 ms)
[----------] 4 tests from NavigationControllerTest (74 ms total)

[----------] Global test environment tear-down
[==========] 5 tests from 1 test cases ran. (136 ms total)
[  PASSED  ] 5 tests.

%(suppression)s
program finished with exit code 255
""" % {'suppression': VALGRIND_SUPPRESSION}


FAILURES_SHARD = ['12>NavigationControllerTest.Reload',
                  '12>NavigationControllerTest/SpdyNetworkTransTest.Constructor/0',
                  '0>BadTest.TimesOut',
                  '12>MoreBadTest.TimesOutAndFails',
                  '0>SomeOtherTest.SwitchTypes']

FAILS_FAILURES_SHARD = ['0>SomeOtherTest.FAILS_Bar']
FLAKY_FAILURES_SHARD = ['0>SomeOtherTest.FLAKY_Baz']

RELOAD_ERRORS_SHARD = r"""12>C:\b\slave\chrome-release-snappy\build\chrome\browser\navigation_controller_unittest.cc:381: Failure
12>Value of: -1
12>Expected: contents->controller()->GetPendingEntryIndex()
12>Which is: 0
12>"""

SPDY_ERRORS_SHARD = r"""12>C:\b\slave\chrome-release-snappy\build\chrome\browser\navigation_controller_unittest.cc:439: Failure
12>Value of: -1
12>Expected: contents->controller()->GetPendingEntryIndex()
12>Which is: 0
12>"""

SWITCH_ERRORS_SHARD = r"""0>C:\b\slave\chrome-release-snappy\build\chrome\browser\navigation_controller_unittest.cc:615: Failure
0>Value of: -1
0>Expected: contents->controller()->GetPendingEntryIndex()
0>Which is: 0
0>
0>C:\b\slave\chrome-release-snappy\build\chrome\browser\navigation_controller_unittest.cc:617: Failure
0>Value of: contents->controller()->GetPendingEntry()
0>  Actual: true
0>Expected: false
0>"""

TIMEOUT_ERRORS_SHARD = """0>[61613:263:0531/042613:2887943745568888:ERROR:/b/slave/chromium-rel-mac-builder/build/src/chrome/browser/extensions/extension_error_reporter.cc(56)] Extension error: Could not load extension from 'extensions/api_test/geolocation/no_permission'. Manifest file is missing or unreadable."""

MOREBAD_ERRORS_SHARD = """12>Value of: entry->page_type()
12>  Actual: 2
12>Expected: NavigationEntry::NORMAL_PAGE"""

TEST_DATA_SHARD_0 = """0>Note: This is test shard 1 of 30.
0>[==========] Running 6 tests from 3 test cases.
0>[----------] Global test environment set-up.
0>[----------] 1 test from HunspellTest
0>[ RUN      ] HunspellTest.All
0>[       OK ] HunspellTest.All (62 ms)
0>[----------] 1 test from HunspellTest (62 ms total)
0>
0>[----------] 1 test from BadTest
0>[ RUN      ] BadTest.TimesOut
%(timeout_errors)s
0>[0531/042642:ERROR:/b/slave/chromium-rel-mac-builder/build/src/chrome/test/test_launcher/out_of_proc_test_runner.cc(79)] Test timeout (30000 ms) exceeded for BadTest.TimesOut
0>Handling SIGTERM.
0>Successfully wrote to shutdown pipe, resetting signal handler.
0>[61613:19971:0531/042642:2887973024284693:INFO:/b/slave/chromium-rel-mac-builder/build/src/chrome/browser/browser_main.cc(285)] Handling shutdown for signal 15.
0>
0>[----------] 4 tests from SomeOtherTest
0>[ RUN      ] SomeOtherTest.SwitchTypes
%(switch_errors)s
0>[  FAILED  ] SomeOtherTest.SwitchTypes (40 ms)
0>[ RUN      ] SomeOtherTest.Foo
0>[       OK ] SomeOtherTest.Foo (20 ms)
0>[ RUN      ] SomeOtherTest.FAILS_Bar
0>Some error message for a failing test.
0>[  FAILED  ] SomeOtherTest.FAILS_Bar (40 ms)
0>[ RUN      ] SomeOtherTest.FLAKY_Baz
0>Some error message for a flaky test.
0>[  FAILED  ] SomeOtherTest.FLAKY_Baz (40 ms)
0>[----------] 2 tests from SomeOtherTest (60 ms total)
0>
0>[----------] Global test environment tear-down
0>[==========] 6 tests from 3 test cases ran. (3750 ms total)
0>[  PASSED  ] 5 tests.
0>[  FAILED  ] 1 test, listed below:
0>[  FAILED  ] SomeOtherTest.SwitchTypes
0>
0> 1 FAILED TEST
0>  YOU HAVE 10 DISABLED TESTS
0>
0>  YOU HAVE 2 FLAKY TESTS
0>""" % {'switch_errors' : SWITCH_ERRORS_SHARD,
       'timeout_errors': TIMEOUT_ERRORS_SHARD}

TEST_DATA_SHARD_1 = """12>Note: This is test shard 13 of 30.
12>[==========] Running 5 tests from 2 test cases.
12>[----------] Global test environment set-up.
12>[----------] 4 tests from NavigationControllerTest
12>[ RUN      ] NavigationControllerTest.Defaults
12>[       OK ] NavigationControllerTest.Defaults (48 ms)
12>[ RUN      ] NavigationControllerTest.Reload
%(reload_errors)s
12>[  FAILED  ] NavigationControllerTest.Reload (2 ms)
12>[ RUN      ] NavigationControllerTest.Reload_GeneratesNewPage
12>[       OK ] NavigationControllerTest.Reload_GeneratesNewPage (22 ms)
12>[ RUN      ] NavigationControllerTest/SpdyNetworkTransTest.Constructor/0
%(spdy_errors)s
12>[  FAILED  ] NavigationControllerTest/SpdyNetworkTransTest.Constructor/0 (2 ms)
12>[----------] 4 tests from NavigationControllerTest (74 ms total)
12>
12>  YOU HAVE 2 FLAKY TESTS
12>
12>[----------] 1 test from MoreBadTest
12>[ RUN      ] MoreBadTest.TimesOutAndFails
%(morebad_errors)s
12>[0531/042642:ERROR:/b/slave/chromium-rel-mac-builder/build/src/chrome/test/test_launcher/out_of_proc_test_runner.cc(79)] Test timeout (30000 ms) exceeded for MoreBadTest.TimesOutAndFails
12>Handling SIGTERM.
12>Successfully wrote to shutdown pipe, resetting signal handler.
12>[  FAILED  ] MoreBadTest.TimesOutAndFails (31000 ms)
12>
12>[----------] Global test environment tear-down
12>[==========] 5 tests from 2 test cases ran. (3750 ms total)
12>[  PASSED  ] 3 tests.
12>[  FAILED  ] 2 tests, listed below:
12>[  FAILED  ] NavigationControllerTest.Reload
12>[  FAILED  ] NavigationControllerTest/SpdyNetworkTransTest.Constructor/0
12>
12> 1 FAILED TEST
12>  YOU HAVE 10 DISABLED TESTS
12>
12>  YOU HAVE 2 FLAKY TESTS
12>""" % {'reload_errors' : RELOAD_ERRORS_SHARD,
       'spdy_errors'   : SPDY_ERRORS_SHARD,
       'morebad_errors': MOREBAD_ERRORS_SHARD}

TEST_DATA_SHARD_EXIT = 'program finished with exit code '

TEST_DATA_CRASH_SHARD = """4>Note: This is test shard 5 of 5.
4>[==========] Running 7 tests from 3 test cases.
4>[----------] Global test environment set-up.
4>[----------] 1 test from HunspellTest
4>[ RUN      ] HunspellTest.Crashes
4>Oops, this test crashed!"""


DUPLICATE_MESSAGE = 'test started more than once'

TEST_DUPLICATE_LINE = '[ RUN      ] HunspellTest.All'

TEST_DATA_DUPLICATE = """
[==========] Running 3 tests from 3 test cases.
[----------] Global test environment set-up.
[----------] 1 test from HunspellTest
[ RUN      ] HunspellTest.All
[       OK ] HunspellTest.All (62 ms)
[----------] 1 test from HunspellTest (62 ms total)

[----------] 1 test from NavigationControllerTest
[ RUN      ] NavigationControllerTest.Defaults
[       OK ] NavigationControllerTest.Defaults (48 ms)
[----------] 1 test from NavigationControllerTest (48 ms total)

[----------] 1 test from HunspellTest
[ RUN      ] HunspellTest.All
[       OK ] HunspellTest.All (26 ms)
[----------] 1 test from HunspellTest (26 ms total)

[----------] Global test environment tear-down
[==========] 3 tests from 3 test cases ran. (136 ms total)
[  PASSED  ] 3 tests.

program finished with exit code 0
"""

TEST_DATA_BAD_DUPLICATE_SHARD_0 = """0>Note: This is test shard 1 of 30.
0>[==========] Running 3 tests from 3 test cases.
0>[----------] Global test environment set-up.
0>[----------] 1 test from HunspellTest
0>[ RUN      ] HunspellTest.All
0>[       OK ] HunspellTest.All (62 ms)
0>[----------] 1 test from HunspellTest (62 ms total)
0>
0>[----------] 1 test from SomeOtherTest
0>[ RUN      ] SomeOtherTest.Foo
0>[       OK ] SomeOtherTest.Foo (20 ms)
0>[----------] 1 test from SomeOtherTest (20 ms total)
0>
0>[----------] 1 test from HunspellTest
0>[ RUN      ] HunspellTest.All
0>[       OK ] HunspellTest.All (26 ms)
0>[----------] 1 test from HunspellTest (26 ms total)
0>
0>[----------] Global test environment tear-down
0>[==========] 3 tests from 3 test cases ran. (108 ms total)
0>[  PASSED  ] 3 tests.
0>
0>  YOU HAVE 10 DISABLED TESTS
0>
0>  YOU HAVE 2 FLAKY TESTS
0>"""

TEST_DATA_OK_DUPLICATE_SHARD_0 = """0>Note: This is test shard 1 of 30.
0>[==========] Running 2 tests from 2 test cases.
0>[----------] Global test environment set-up.
0>[----------] 1 test from HunspellTest
0>[ RUN      ] HunspellTest.All
0>[       OK ] HunspellTest.All (62 ms)
0>[----------] 1 test from HunspellTest (62 ms total)
0>
0>[----------] 1 test from NavigationControllerTest
0>[ RUN      ] NavigationControllerTest.Defaults
0>[       OK ] NavigationControllerTest.Defaults (48 ms)
0>[----------] 1 test from NavigationControllerTest (48 ms total)
0>
0>[----------] Global test environment tear-down
0>[==========] 2 tests from 2 test cases ran. (110 ms total)
0>[  PASSED  ] 2 tests.
0>
0>  YOU HAVE 10 DISABLED TESTS
0>
0>  YOU HAVE 2 FLAKY TESTS
0>"""


class TestObserverTests(unittest.TestCase):
  def AlternateShards(self, shard_0, shard_1):
    # Returns a list of alternating lines from the two shards such that the
    # temporal order within shards is preserved.
    test_data_shard_0 = shard_0.split('\n')
    test_data_shard_0.reverse()
    test_data_shard_1 = shard_1.split('\n')
    test_data_shard_1.reverse()
    test_data_shard = []
    which = 0
    while test_data_shard_0 or test_data_shard_1:
      if which % 2 and test_data_shard_0:
        test_data_shard.append(test_data_shard_0.pop())
      elif test_data_shard_1:
        test_data_shard.append(test_data_shard_1.pop())
      which += 1
    return test_data_shard

  def testLogLineObserver(self):
    # Tests for log parsing without sharding.
    observer = gtest_command.TestObserver()
    for line in TEST_DATA.splitlines():
      observer.outLineReceived(line)

    self.assertEqual(0, len(observer.internal_error_lines))
    self.assertFalse(observer.RunningTests())

    self.assertEqual(sorted(FAILURES), sorted(observer.FailedTests()))
    self.assertEqual(sorted(FAILURES + FAILS_FAILURES),
                     sorted(observer.FailedTests(include_fails=True)))
    self.assertEqual(sorted(FAILURES + FLAKY_FAILURES),
                     sorted(observer.FailedTests(include_flaky=True)))
    self.assertEqual(sorted(FAILURES + FAILS_FAILURES + FLAKY_FAILURES),
        sorted(observer.FailedTests(include_fails=True, include_flaky=True)))

    self.assertEqual(10, observer.disabled_tests)
    self.assertEqual(2, observer.flaky_tests)

    test_name = 'NavigationControllerTest.Reload'
    self.assertEqual('\n'.join(['%s: ' % test_name, RELOAD_ERRORS]),
                     '\n'.join(observer.FailureDescription(test_name)))

    test_name = 'NavigationControllerTest/SpdyNetworkTransTest.Constructor/0'
    self.assertEqual('\n'.join(['%s: ' % test_name, SPDY_ERRORS]),
                     '\n'.join(observer.FailureDescription(test_name)))

    test_name = 'SomeOtherTest.SwitchTypes'
    self.assertEqual('\n'.join(['%s: ' % test_name, SWITCH_ERRORS]),
                     '\n'.join(observer.FailureDescription(test_name)))

    test_name = 'BadTest.TimesOut'
    self.assertEqual('\n'.join(['%s: ' % test_name,
                                TIMEOUT_ERRORS, TIMEOUT_MESSAGE]),
                     '\n'.join(observer.FailureDescription(test_name)))

    test_name = 'MoreBadTest.TimesOutAndFails'
    self.assertEqual('\n'.join(['%s: ' % test_name,
                                MOREBAD_ERRORS, TIMEOUT_MESSAGE]),
                     '\n'.join(observer.FailureDescription(test_name)))

    observer = gtest_command.TestObserver()
    for line in TEST_DATA_CRASH.splitlines():
      observer.outLineReceived(line)

    self.assertEqual(0, len(observer.internal_error_lines))
    self.assertTrue(observer.RunningTests())
    self.assertEqual(['HunspellTest.Crashes'], observer.FailedTests())
    self.assertEqual(0, observer.disabled_tests)
    self.assertEqual(0, observer.flaky_tests)

    test_name = 'HunspellTest.Crashes'
    self.assertEqual('\n'.join(['%s: ' % test_name, 'Did not complete.']),
                     '\n'.join(observer.FailureDescription(test_name)))

    observer = gtest_command.TestObserver()
    for line in TEST_DATA_VALGRIND.splitlines():
      observer.outLineReceived(line)

    self.assertEqual(0, len(observer.internal_error_lines))
    self.assertFalse(observer.RunningTests())
    self.assertFalse(observer.FailedTests())
    self.assertEqual([VALGRIND_HASH], observer.SuppressionHashes())
    self.assertEqual(VALGRIND_SUPPRESSION,
                     '\n'.join(observer.Suppression(VALGRIND_HASH)))

    # Same tests for log parsing with sharding_supervisor.
    observer = gtest_command.TestObserver()
    test_data_shard = self.AlternateShards(
        TEST_DATA_SHARD_0, TEST_DATA_SHARD_1)
    for line in test_data_shard:
      observer.outLineReceived(line)
    observer.outLineReceived(TEST_DATA_SHARD_EXIT + '2')

    self.assertEqual(0, len(observer.internal_error_lines))
    self.assertFalse(observer.RunningTests())

    self.assertEqual(sorted(FAILURES_SHARD), sorted(observer.FailedTests()))
    self.assertEqual(sorted(FAILURES_SHARD + FAILS_FAILURES_SHARD),
                     sorted(observer.FailedTests(include_fails=True)))
    self.assertEqual(sorted(FAILURES_SHARD + FLAKY_FAILURES_SHARD),
                     sorted(observer.FailedTests(include_flaky=True)))
    self.assertEqual(sorted(
        FAILURES_SHARD + FAILS_FAILURES_SHARD + FLAKY_FAILURES_SHARD),
        sorted(observer.FailedTests(include_fails=True, include_flaky=True)))

    self.assertEqual(10, observer.disabled_tests)
    self.assertEqual(2, observer.flaky_tests)

    test_name = '12>NavigationControllerTest.Reload'
    self.assertEqual('\n'.join(['%s: ' % test_name, RELOAD_ERRORS_SHARD]),
                     '\n'.join(observer.FailureDescription(test_name)))

    test_name = (
        '12>NavigationControllerTest/SpdyNetworkTransTest.Constructor/0')
    self.assertEqual('\n'.join(['%s: ' % test_name, SPDY_ERRORS_SHARD]),
                     '\n'.join(observer.FailureDescription(test_name)))

    test_name = '0>SomeOtherTest.SwitchTypes'
    self.assertEqual('\n'.join(['%s: ' % test_name, SWITCH_ERRORS_SHARD]),
                     '\n'.join(observer.FailureDescription(test_name)))

    test_name = 'BadTest.TimesOut'
    test_shard = '0>'
    test_sharded_name = test_shard + test_name
    self.assertEqual(
        '\n'.join(['%s: ' % test_sharded_name,
        TIMEOUT_ERRORS_SHARD, TIMEOUT_MESSAGE]),
        '\n'.join(observer.FailureDescription(test_sharded_name)))

    test_name = 'MoreBadTest.TimesOutAndFails'
    test_shard = '12>'
    test_sharded_name = test_shard + test_name
    self.assertEqual(
        '\n'.join(['%s: ' % test_sharded_name,
        MOREBAD_ERRORS_SHARD, TIMEOUT_MESSAGE]),
        '\n'.join(observer.FailureDescription(test_sharded_name)))

    observer = gtest_command.TestObserver()
    for line in TEST_DATA_CRASH_SHARD.splitlines():
      observer.outLineReceived(line)

    self.assertEqual(0, len(observer.internal_error_lines))
    self.assertTrue(observer.RunningTests())
    self.assertEqual(['4>HunspellTest.Crashes'], observer.FailedTests())
    self.assertEqual(0, observer.disabled_tests)
    self.assertEqual(0, observer.flaky_tests)

    test_name = '4>HunspellTest.Crashes'
    self.assertEqual('\n'.join(['%s: ' % test_name, 'Did not complete.']),
                     '\n'.join(observer.FailureDescription(test_name)))

    # Test that duplicates are caught when not sharding.
    observer = gtest_command.TestObserver()
    for line in TEST_DATA_DUPLICATE.splitlines():
      observer.outLineReceived(line)

    self.assertEqual(1, len(observer.internal_error_lines))
    self.assertFalse(observer.RunningTests())

    test_reasons = [line.split(': ')[1]
                    for line in observer.internal_error_lines]
    self.assertTrue(
        '%s [%s]' % (TEST_DUPLICATE_LINE, DUPLICATE_MESSAGE) in test_reasons)

    # Test that duplicates are caught when they are in the same shard.
    observer = gtest_command.TestObserver()
    test_data_shard = self.AlternateShards(
        TEST_DATA_BAD_DUPLICATE_SHARD_0, TEST_DATA_SHARD_1)
    for line in test_data_shard:
      observer.outLineReceived(line)
    observer.outLineReceived(TEST_DATA_SHARD_EXIT + '1')

    self.assertEqual(1, len(observer.internal_error_lines))
    self.assertFalse(observer.RunningTests())

    test_shard = '0>'
    test_reasons = [line.split(': ')[1]
                    for line in observer.internal_error_lines]
    self.assertTrue('%s%s [%s]' % (
        test_shard, TEST_DUPLICATE_LINE, DUPLICATE_MESSAGE) in test_reasons)

    # Test that duplicates are ignored when they are in different shards.
    observer = gtest_command.TestObserver()
    test_data_shard = self.AlternateShards(
        TEST_DATA_OK_DUPLICATE_SHARD_0, TEST_DATA_SHARD_1)
    for line in test_data_shard:
      observer.outLineReceived(line)
    observer.outLineReceived(TEST_DATA_SHARD_EXIT + '1')

    self.assertEqual(0, len(observer.internal_error_lines))
    self.assertFalse(observer.RunningTests())


if __name__ == '__main__':
  unittest.main()
